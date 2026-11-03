from unittest.mock import MagicMock
from app.services.publisher_service import PublisherService
from app.services.approval_service import ApprovalService
from app.models.media_asset import MediaAsset
from app.models.post_draft import PostDraft
from app.models.scheduled_post import ScheduledPost
from app.models.publish_attempt import PublishAttempt
from app.core.timezone import get_current_time_utc


def test_timeout_transitions_to_unknown_and_reconciles_safely(db_session):
    asset = MediaAsset(
        drive_file_id="asset_timeout_01",
        name="video_timeout.mp4",
        sha256_hash="hash_timeout_01",
        file_size_bytes=1000,
        status="READY"
    )
    db_session.add(asset)
    db_session.commit()

    draft = PostDraft(
        media_asset_id=asset.id,
        title="Timeout Test",
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
    
    # Simula erro de timeout remoto durante o upload
    pub_svc.tiktok_adapter.upload_video_binary = MagicMock(side_effect=TimeoutError("Gateway Timeout"))

    # Executa a publicação: como o publish_id já foi obtido na inicialização,
    # a falha pós-inicialização DEVE marcar como UNKNOWN / RECONCILING, sem disparar novas tentativas cegas
    res = pub_svc.execute_publish(post.id)
    assert res["status"] == "UNKNOWN"

    db_session.refresh(post)
    assert post.status == "UNKNOWN"

    attempt = db_session.query(PublishAttempt).filter_by(scheduled_post_id=post.id).first()
    assert attempt is not None
    assert attempt.publish_id is not None
    assert attempt.status == "UNKNOWN"

    # Agora simula a reconciliação com o TikTok respondendo que a publicação foi concluída
    pub_svc.tiktok_adapter.fetch_publish_status = MagicMock(return_value={"status": "PUBLISH_COMPLETE"})
    reconciled_count = pub_svc.reconcile_unknown_posts()

    assert reconciled_count == 1
    db_session.refresh(post)
    assert post.status == "PUBLISHED"
