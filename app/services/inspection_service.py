import logging
from sqlalchemy.orm import Session
from app.models.media_asset import MediaAsset
from app.models.post_draft import PostDraft
from app.models.account import Account
from app.models.audit_event import AuditEvent
from app.adapters.media_inspector import MediaInspector
from app.adapters.ai_caption import AICaptionAdapter

logger = logging.getLogger(__name__)


class InspectionService:
    def __init__(self, db: Session):
        self.db = db
        self.inspector = MediaInspector()
        self.caption_adapter = AICaptionAdapter()

    def inspect_asset(self, asset_id: str) -> MediaAsset:
        asset = self.db.query(MediaAsset).filter_by(id=asset_id).first()
        if not asset:
            raise ValueError(f"Ativo de mídia {asset_id} não encontrado.")

        asset.status = "VALIDATING"
        self.db.commit()

        report = self.inspector.inspect(asset.local_storage_path or "")
        
        asset.duration_seconds = report.duration_seconds
        asset.width = report.width
        asset.height = report.height
        asset.aspect_ratio = report.aspect_ratio
        asset.video_codec = report.video_codec
        asset.audio_codec = report.audio_codec
        asset.has_audio = "yes" if report.has_audio else "no"
        asset.validation_notes = " | ".join(report.reasons) if report.reasons else "Conforme com especificações TikTok."

        # Gerar rascunho de legenda inicial
        caption_info = self.caption_adapter.generate_caption(asset.name)

        # Buscar conta primária ativa para associar
        account = self.db.query(Account).filter_by(is_active=True).first()

        existing_draft = self.db.query(PostDraft).filter_by(media_asset_id=asset.id).first()
        if not existing_draft:
            draft = PostDraft(
                media_asset_id=asset.id,
                account_id=account.id if account else None,
                title=caption_info["title"],
                caption=caption_info["caption"],
                hashtags=caption_info["hashtags"],
                privacy_level="PUBLIC_TO_EVERYONE" if account and "PUBLIC_TO_EVERYONE" in (account.privacy_options or "") else "SELF_ONLY",
                disable_comment=False,
                disable_duet=False,
                disable_stitch=False,
                is_aigc=False,
                status="NEEDS_REVIEW" if not report.is_compatible else "READY",
                validation_notes=asset.validation_notes
            )
            self.db.add(draft)

        if report.is_compatible:
            asset.status = "READY"
        else:
            asset.status = "NEEDS_REVIEW"

        audit = AuditEvent(
            action="MEDIA_INSPECTED",
            entity_type="media_asset",
            entity_id=asset.id,
            user_or_system="worker",
            details=f"Status: {asset.status}, Duração: {asset.duration_seconds}s, Resolução: {asset.width}x{asset.height}, Codec: {asset.video_codec}"
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def inspect_all_pending(self) -> int:
        pending_assets = self.db.query(MediaAsset).filter(
            MediaAsset.status.in_(["DISCOVERED", "VALIDATING"])
        ).all()
        for asset in pending_assets:
            self.inspect_asset(asset.id)
        return len(pending_assets)
