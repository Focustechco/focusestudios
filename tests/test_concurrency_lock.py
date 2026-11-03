from datetime import datetime, timedelta
from app.services.publisher_service import PublisherService
from app.models.scheduled_post import ScheduledPost
from app.models.post_draft import PostDraft
from app.models.media_asset import MediaAsset
from app.core.timezone import get_current_time_utc


def test_concurrent_worker_reservation(db_session):
    # Criar ativo e rascunho
    asset = MediaAsset(
        drive_file_id="asset_lock_01",
        name="video_lock.mp4",
        sha256_hash="hash_lock_01",
        file_size_bytes=1000,
        status="READY"
    )
    db_session.add(asset)
    db_session.commit()

    draft = PostDraft(
        media_asset_id=asset.id,
        title="Lock Test",
        caption="Caption",
        status="APPROVED"
    )
    db_session.add(draft)
    db_session.commit()

    # Post agendado para o passado imediato (pronto para envio)
    past_time_utc = get_current_time_utc() - timedelta(minutes=2)
    post = ScheduledPost(
        post_draft_id=draft.id,
        scheduled_time_utc=past_time_utc,
        status="SCHEDULED"
    )
    db_session.add(post)
    db_session.commit()

    pub_svc_1 = PublisherService(db_session)
    pub_svc_2 = PublisherService(db_session)

    # Worker 1 reserva os jobs prontos
    claimed_1 = pub_svc_1.claim_due_scheduled_posts(worker_id="worker_alpha", limit=1)
    assert len(claimed_1) == 1
    assert claimed_1[0].id == post.id
    assert claimed_1[0].lock_id == "worker_alpha"
    assert claimed_1[0].status == "UPLOADING"

    # Worker 2 concorrente tenta reservar no mesmo instante: não deve receber o mesmo job!
    claimed_2 = pub_svc_2.claim_due_scheduled_posts(worker_id="worker_beta", limit=1)
    assert len(claimed_2) == 0
