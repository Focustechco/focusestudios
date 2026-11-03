from datetime import datetime
from sqlalchemy.orm import Session
from app.models.post_draft import PostDraft
from app.models.approval import Approval
from app.models.account import Account
from app.models.scheduled_post import ScheduledPost
from app.models.audit_event import AuditEvent
from app.core.security import calculate_content_hash
from app.core.timezone import get_current_time_utc


class ApprovalService:
    def __init__(self, db: Session):
        self.db = db

    def update_draft(
        self,
        draft_id: str,
        title: str,
        caption: str,
        hashtags: str,
        privacy_level: str,
        disable_comment: bool,
        disable_duet: bool,
        disable_stitch: bool,
        is_aigc: bool,
        brand_content_toggle: bool,
        brand_organic_toggle: bool
    ) -> PostDraft:
        draft = self.db.query(PostDraft).filter_by(id=draft_id).first()
        if not draft:
            raise ValueError("Rascunho não encontrado.")

        # Verificar se houve alteração de conteúdo relevante
        content_changed = (
            draft.title != title or
            draft.caption != caption or
            draft.hashtags != hashtags or
            draft.privacy_level != privacy_level or
            draft.disable_comment != disable_comment or
            draft.disable_duet != disable_duet or
            draft.disable_stitch != disable_stitch or
            draft.is_aigc != is_aigc or
            draft.brand_content_toggle != brand_content_toggle or
            draft.brand_organic_toggle != brand_organic_toggle
        )

        draft.title = title
        draft.caption = caption
        draft.hashtags = hashtags
        draft.privacy_level = privacy_level
        draft.disable_comment = disable_comment
        draft.disable_duet = disable_duet
        draft.disable_stitch = disable_stitch
        draft.is_aigc = is_aigc
        draft.brand_content_toggle = brand_content_toggle
        draft.brand_organic_toggle = brand_organic_toggle

        # Regra fundamental: Alterações relevantes invalidam aprovações ativas
        if content_changed:
            active_approvals = self.db.query(Approval).filter_by(post_draft_id=draft.id, is_active=True).all()
            for app in active_approvals:
                app.is_active = False
                app.revoked_at = get_current_time_utc()
                app.revocation_reason = "Conteúdo alterado após aprovação."

            # Se estava aprovado ou agendado, deve retornar para NEEDS_REVIEW
            if draft.status in ("APPROVED", "SCHEDULED"):
                draft.status = "NEEDS_REVIEW"
                draft.validation_notes = "Aprovação invalidada devido a edições no texto ou configurações."
                
                # Se tinha agendamento pendente, cancela para exigir novo consentimento
                scheduled = self.db.query(ScheduledPost).filter_by(post_draft_id=draft.id, status="SCHEDULED").first()
                if scheduled:
                    scheduled.status = "NEEDS_REVIEW"

        self.db.commit()
        self.db.refresh(draft)
        return draft

    def approve_draft(self, draft_id: str, approved_by: str = "operador") -> Approval:
        draft = self.db.query(PostDraft).filter_by(id=draft_id).first()
        if not draft:
            raise ValueError("Rascunho não encontrado.")

        # Validar opções de privacidade com a conta
        if draft.account and draft.account.privacy_options:
            allowed = [opt.strip() for opt in draft.account.privacy_options.split(",")]
            if draft.privacy_level not in allowed:
                raise ValueError(
                    f"Nível de privacidade '{draft.privacy_level}' não é permitido para esta conta. Opções: {allowed}"
                )

        media_sha256 = draft.media_asset.sha256_hash if draft.media_asset else "unknown"
        content_hash = calculate_content_hash(
            media_sha256=media_sha256,
            title=f"{draft.title} {draft.caption} {draft.hashtags}",
            privacy_level=draft.privacy_level,
            disable_comment=draft.disable_comment,
            disable_duet=draft.disable_duet,
            disable_stitch=draft.disable_stitch,
            is_aigc=draft.is_aigc,
            brand_content=draft.brand_content_toggle or draft.brand_organic_toggle
        )

        # Desativa aprovações anteriores se houver
        self.db.query(Approval).filter_by(post_draft_id=draft.id, is_active=True).update({
            "is_active": False,
            "revoked_at": get_current_time_utc(),
            "revocation_reason": "Substituído por nova aprovação explícita."
        })

        approval = Approval(
            post_draft_id=draft.id,
            approved_by=approved_by,
            approved_at=get_current_time_utc(),
            content_hash=content_hash,
            is_active=True
        )
        self.db.add(approval)
        draft.status = "APPROVED"
        draft.validation_notes = "Aprovado com consentimento explícito registrado."

        audit = AuditEvent(
            action="DRAFT_APPROVED",
            entity_type="post_draft",
            entity_id=draft.id,
            user_or_system=approved_by,
            details=f"Hash de consentimento: {content_hash[:16]}... | Privacidade: {draft.privacy_level}"
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(approval)
        return approval
