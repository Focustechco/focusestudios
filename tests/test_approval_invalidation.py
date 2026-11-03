from app.services.approval_service import ApprovalService
from app.models.media_asset import MediaAsset
from app.models.post_draft import PostDraft
from app.models.approval import Approval
from app.models.scheduled_post import ScheduledPost
from app.core.timezone import get_current_time_utc


def test_approval_and_invalidation_after_content_edit(db_session):
    asset = MediaAsset(
        drive_file_id="asset_app_01",
        name="video_approval.mp4",
        sha256_hash="hash_approval_01",
        file_size_bytes=1000,
        status="READY"
    )
    db_session.add(asset)
    db_session.commit()

    draft = PostDraft(
        media_asset_id=asset.id,
        title="Original Title",
        caption="Original Caption",
        hashtags="#original",
        privacy_level="PUBLIC_TO_EVERYONE",
        status="READY"
    )
    db_session.add(draft)
    db_session.commit()

    app_svc = ApprovalService(db_session)

    # 1. Aprova o rascunho: gera hash e consentimento ativo
    approval = app_svc.approve_draft(draft.id, approved_by="admin_user")
    assert approval.is_active is True
    assert draft.status == "APPROVED"
    original_hash = approval.content_hash

    # 2. Modifica a legenda do rascunho
    updated_draft = app_svc.update_draft(
        draft_id=draft.id,
        title="Modified Title",
        caption="Modified Caption",
        hashtags="#modified",
        privacy_level="PUBLIC_TO_EVERYONE",
        disable_comment=False,
        disable_duet=False,
        disable_stitch=False,
        is_aigc=False,
        brand_content_toggle=False,
        brand_organic_toggle=False
    )

    # 3. Verifica se a aprovação anterior foi revogada e o status rebaixado
    db_session.refresh(approval)
    assert approval.is_active is False
    assert approval.revocation_reason == "Conteúdo alterado após aprovação."
    assert updated_draft.status == "NEEDS_REVIEW"
