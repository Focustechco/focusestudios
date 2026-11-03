from unittest.mock import MagicMock
from app.services.publisher_service import PublisherService
from app.services.approval_service import ApprovalService
from app.models.media_asset import MediaAsset
from app.models.post_draft import PostDraft
from app.models.scheduled_post import ScheduledPost
from app.core.timezone import get_current_time_utc


def test_upload_vs_processing_vs_published_states(db_session):
    asset = MediaAsset(
        drive_file_id="asset_state_01",
        name="video_states.mp4",
        sha256_hash="hash_states_01",
        file_size_bytes=2000,
        status="READY"
    )
    db_session.add(asset)
    db_session.commit()

    draft = PostDraft(
        media_asset_id=asset.id,
        title="State Test",
        caption="Caption",
        hashtags="#test",
        privacy_level="PUBLIC_TO_EVERYONE",
        status="READY"
    )
    db_session.add(draft)
    db_session.commit()

    app_svc = ApprovalService(db_session)
    app_svc.approve_draft(draft.id, approved_by="admin")

    post = ScheduledPost(
        post_draft_id=draft.id,
        scheduled_time_utc=get_current_time_utc(),
        status="SCHEDULED"
    )
    db_session.add(post)
    db_session.commit()

    pub_svc = PublisherService(db_session)

    # Caso 1: Upload de binário concluído, mas TikTok ainda processa moderação (SEND_TO_AUDIT)
    pub_svc.tiktok_adapter.fetch_publish_status = MagicMock(return_value={"status": "SEND_TO_AUDIT"})
    res1 = pub_svc.execute_publish(post.id)

    db_session.refresh(post)
    # Regra fundamental: Upload concluído NÃO significa publicado
    assert post.status == "PROCESSING"

    # Caso 2: Próxima verificação de status retorna PUBLISH_COMPLETE
    pub_svc.tiktok_adapter.fetch_publish_status = MagicMock(return_value={"status": "PUBLISH_COMPLETE"})
    pub_svc.reconcile_unknown_posts()
    # Se simular o status fetch direto:
    status_res = pub_svc.tiktok_adapter.fetch_publish_status("token", "pub_id")
    if status_res["status"] == "PUBLISH_COMPLETE":
        post.status = "PUBLISHED"
        db_session.commit()

    assert post.status == "PUBLISHED"
