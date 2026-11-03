import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.config import settings
from app.models.scheduled_post import ScheduledPost
from app.models.post_draft import PostDraft
from app.models.approval import Approval
from app.models.account import Account
from app.models.publish_attempt import PublishAttempt
from app.models.audit_event import AuditEvent
from app.adapters.tiktok.mock_tiktok import MockTikTokAdapter
from app.adapters.tiktok.direct_post import TikTokDirectPostAdapter
from app.core.security import calculate_content_hash
from app.core.timezone import get_current_time_utc, to_utc

logger = logging.getLogger(__name__)


class PublisherService:
    def __init__(self, db: Session):
        self.db = db
        if settings.OPERATION_MODE == "DEMO":
            self.tiktok_adapter = MockTikTokAdapter()
        else:
            self.tiktok_adapter = TikTokDirectPostAdapter()

    def claim_due_scheduled_posts(self, worker_id: str, limit: int = 5) -> List[ScheduledPost]:
        """
        Reserva atômica de jobs agendados que atingiram o horário (now_utc).
        Utiliza SELECT FOR UPDATE SKIP LOCKED quando suportado pelo banco (PostgreSQL),
        impedindo que múltiplos workers executem o mesmo post em paralelo.
        """
        now_utc = get_current_time_utc()
        lock_timeout = now_utc - timedelta(minutes=10)  # Recupera locks mortos após 10min

        query = self.db.query(ScheduledPost).filter(
            ScheduledPost.status == "SCHEDULED",
            ScheduledPost.scheduled_time_utc <= now_utc,
            or_(
                ScheduledPost.locked_at == None,
                ScheduledPost.locked_at < lock_timeout
            )
        ).order_by(ScheduledPost.scheduled_time_utc.asc())

        # Tenta aplicar with_for_update(skip_locked=True)
        try:
            posts = query.with_for_update(skip_locked=True).limit(limit).all()
        except Exception:
            # Fallback seguro para dialetos como SQLite
            posts = query.limit(limit).all()

        claimed = []
        for post in posts:
            # Proteção contra disparo em rajada após indisponibilidade:
            # Se o post estiver atrasado além da tolerância, não dispara; vai para revisão
            post_time_utc = to_utc(post.scheduled_time_utc)
            delay_minutes = (now_utc - post_time_utc).total_seconds() / 60.0
            if delay_minutes > settings.OVERDUE_TOLERANCE_MINUTES:
                post.status = "NEEDS_REVIEW"
                post.lock_id = None
                post.locked_at = None
                audit = AuditEvent(
                    action="OVERDUE_POST_FLAGGED",
                    entity_type="scheduled_post",
                    entity_id=post.id,
                    user_or_system=worker_id,
                    details=f"Post atrasado por {delay_minutes:.1f} min (> {settings.OVERDUE_TOLERANCE_MINUTES} min). Requer revisão para evitar rajada de spam."
                )
                self.db.add(audit)
                continue

            post.status = "UPLOADING"
            post.lock_id = worker_id
            post.locked_at = now_utc
            claimed.append(post)

        self.db.commit()
        return claimed

    def execute_publish(self, scheduled_post_id: str) -> Dict[str, Any]:
        """
        Executa a publicação de um post reservado.
        Valida o consentimento ativo, hash criptográfico, inicializa upload no TikTok,
        salva o publish_id imediatamente e monitora status.
        """
        post = self.db.query(ScheduledPost).filter_by(id=scheduled_post_id).first()
        if not post:
            return {"status": "error", "message": "Post agendado não encontrado."}

        draft: PostDraft = post.post_draft
        account: Optional[Account] = post.account or self.db.query(Account).filter_by(is_active=True).first()

        # 1. Validação de Consentimento Ativo
        active_approval = self.db.query(Approval).filter_by(
            post_draft_id=draft.id,
            is_active=True
        ).first()

        if not active_approval:
            post.status = "NEEDS_REVIEW"
            post.lock_id = None
            self.db.commit()
            return {"status": "error", "message": "Publicação bloqueada: consentimento explícito ativo não encontrado."}

        # 2. Verificação de Integridade Criptográfica (Hash)
        media_sha256 = draft.media_asset.sha256_hash if draft.media_asset else "unknown"
        expected_hash = calculate_content_hash(
            media_sha256=media_sha256,
            title=f"{draft.title} {draft.caption} {draft.hashtags}",
            privacy_level=draft.privacy_level,
            disable_comment=draft.disable_comment,
            disable_duet=draft.disable_duet,
            disable_stitch=draft.disable_stitch,
            is_aigc=draft.is_aigc,
            brand_content=draft.brand_content_toggle or draft.brand_organic_toggle
        )

        if active_approval.content_hash != expected_hash:
            post.status = "NEEDS_REVIEW"
            active_approval.is_active = False
            active_approval.revoked_at = get_current_time_utc()
            active_approval.revocation_reason = "Hash de conteúdo divergente do aprovado."
            self.db.commit()
            return {"status": "error", "message": "Publicação bloqueada: conteúdo foi alterado após a aprovação."}

        # 3. Validação de Elegibilidade em Modo Produção (DIRECT_POST)
        if settings.OPERATION_MODE == "DIRECT_POST":
            if not account or not account.is_eligible or account.is_token_expired():
                post.status = "BLOCKED"
                self.db.commit()
                return {"status": "blocked", "message": "Bloqueado: Conta sem autorização ou elegibilidade Direct Post."}

        # 4. Criar tentativa de publicação
        attempt = PublishAttempt(
            scheduled_post_id=post.id,
            attempt_number=len(post.publish_attempts) + 1,
            status="UPLOADING",
            started_at=get_current_time_utc()
        )
        self.db.add(attempt)
        self.db.commit()

        try:
            # 5. Inicialização no TikTok
            post_info = {
                "title": f"{draft.title} {draft.caption} {draft.hashtags}".strip(),
                "privacy_level": draft.privacy_level,
                "disable_comment": draft.disable_comment,
                "disable_duet": draft.disable_duet,
                "disable_stitch": draft.disable_stitch,
                "brand_content_toggle": draft.brand_content_toggle,
                "brand_organic_toggle": draft.brand_organic_toggle,
                "is_aigc": draft.is_aigc
            }
            file_path = draft.media_asset.local_storage_path or ""
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 1000
            source_info = {
                "source": "FILE_UPLOAD",
                "video_size": file_size,
                "chunk_size": file_size,
                "total_chunk_count": 1
            }

            token = account.access_token if account else "demo_token"
            init_res = self.tiktok_adapter.init_video_publish(token, post_info, source_info)
            
            publish_id = init_res.get("publish_id")
            upload_url = init_res.get("upload_url")

            # Salvar publish_id imediatamente
            attempt.publish_id = publish_id
            attempt.status = "UPLOADING"
            post.status = "UPLOADING"
            self.db.commit()

            # 6. Upload de Binário
            self.tiktok_adapter.upload_video_binary(upload_url, file_path)
            
            # Atualiza para PROCESSING (upload concluído != publicado)
            attempt.status = "PROCESSING"
            post.status = "PROCESSING"
            self.db.commit()

            # 7. Polling de status inicial
            status_res = self.tiktok_adapter.fetch_publish_status(token, publish_id)
            tiktok_status = status_res.get("status")

            if tiktok_status == "PUBLISH_COMPLETE":
                attempt.status = "PUBLISHED"
                attempt.completed_at = get_current_time_utc()
                post.status = "PUBLISHED"
            elif tiktok_status in ("PROCESSING_UPLOAD", "PROCESSING_DOWNLOAD", "SEND_TO_AUDIT"):
                post.status = "PROCESSING"
            elif tiktok_status == "FAILED":
                post.status = "FAILED"
                attempt.status = "FAILED"
                attempt.error_message = status_res.get("fail_reason", "Falha de moderação no TikTok")
            
            self.db.commit()
            return {"status": post.status, "publish_id": publish_id}

        except Exception as e:
            logger.error(f"Erro na publicação do post {post.id}: {str(e)}")
            # Regra fundamental: Timeout após chamada com possível efeito remoto marca UNKNOWN/RECONCILING
            if attempt.publish_id:
                post.status = "UNKNOWN"
                attempt.status = "UNKNOWN"
                attempt.error_message = f"Timeout ou falha pós-inicialização: {str(e)}"
            else:
                post.status = "FAILED"
                attempt.status = "FAILED"
                attempt.error_message = str(e)

            self.db.commit()
            return {"status": post.status, "error": str(e)}

    def reconcile_unknown_posts(self) -> int:
        """
        Tarefa de reconciliação para posts em estado UNKNOWN.
        Consulta a API do TikTok pelo publish_id gravado, sem reenviar nova publicação.
        """
        unknown_posts = self.db.query(ScheduledPost).filter_by(status="UNKNOWN").all()
        reconciled = 0

        for post in unknown_posts:
            last_attempt = self.db.query(PublishAttempt).filter_by(
                scheduled_post_id=post.id
            ).order_by(PublishAttempt.attempt_number.desc()).first()

            if not last_attempt or not last_attempt.publish_id:
                post.status = "FAILED"
                continue

            try:
                token = post.account.access_token if post.account else "demo_token"
                status_res = self.tiktok_adapter.fetch_publish_status(token, last_attempt.publish_id)
                tiktok_status = status_res.get("status")

                if tiktok_status == "PUBLISH_COMPLETE":
                    post.status = "PUBLISHED"
                    last_attempt.status = "PUBLISHED"
                    last_attempt.completed_at = get_current_time_utc()
                    reconciled += 1
                elif tiktok_status in ("PROCESSING_UPLOAD", "PROCESSING_DOWNLOAD", "SEND_TO_AUDIT"):
                    post.status = "PROCESSING"
                    last_attempt.status = "PROCESSING"
                elif tiktok_status == "FAILED":
                    post.status = "FAILED"
                    last_attempt.status = "FAILED"
                    last_attempt.error_message = status_res.get("fail_reason", "Falha remota confirmada")
                    reconciled += 1

            except Exception as ex:
                logger.warning(f"Reconciliação pendente para post {post.id}: {str(ex)}")

        self.db.commit()
        return reconciled
