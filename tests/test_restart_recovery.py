from datetime import datetime, timedelta
from app.services.publisher_service import PublisherService
from app.models.scheduled_post import ScheduledPost
from app.models.post_draft import PostDraft
from app.models.media_asset import MediaAsset
from app.models.approval import Approval
from app.core.timezone import get_current_time_utc
from app.config import settings


def test_recovery_after_restart_and_delayed_job_protection(db_session):
    # Simula situação onde o worker caiu enquanto processava e o job ficou preso no passado
    asset = MediaAsset(
        drive_file_id="asset_recovery_01",
        name="video_recovery.mp4",
        sha256_hash="hash_recovery_01",
        file_size_bytes=1000,
        status="READY"
    )
    db_session.add(asset)
    db_session.commit()

    draft = PostDraft(
        media_asset_id=asset.id,
        title="Recovery Test",
        caption="Caption",
        hashtags="#test",
        privacy_level="PUBLIC_TO_EVERYONE",
        status="READY"
    )
    db_session.add(draft)
    db_session.commit()

    # Job agendado para 2 horas atrás (muito além da tolerância de 15 minutos)
    stale_time_utc = get_current_time_utc() - timedelta(hours=2)
    post = ScheduledPost(
        post_draft_id=draft.id,
        scheduled_time_utc=stale_time_utc,
        status="SCHEDULED",
        lock_id="old_dead_worker",
        locked_at=stale_time_utc
    )
    db_session.add(post)
    db_session.commit()

    pub_svc = PublisherService(db_session)
    # Novo worker reiniciado tenta reivindicar os jobs
    claimed = pub_svc.claim_due_scheduled_posts(worker_id="new_restarted_worker", limit=5)

    # Regra fundamental: Não disparar em rajada jobs com atraso excessivo pós-queda
    # O job deve ser protegido e colocado em NEEDS_REVIEW para reagendamento seguro
    assert len(claimed) == 0

    db_session.refresh(post)
    assert post.status == "NEEDS_REVIEW"
    assert post.lock_id is None
