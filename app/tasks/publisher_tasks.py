import os
import uuid
import logging
from app.tasks.celery_app import celery_app
from app.database import get_db_context
from app.services.publisher_service import PublisherService
from app.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.publisher_tasks.task_check_and_publish_due")
def task_check_and_publish_due():
    """
    Executa a cada minuto via Celery Beat.
    Reserva de forma atômica os posts agendados no banco (PostgreSQL source of truth)
    e dispara a execução.
    """
    # No modo MANUAL_STUDIO não dispara publicação automática
    if settings.OPERATION_MODE == "MANUAL_STUDIO":
        return {"status": "skipped", "reason": "Modo MANUAL_STUDIO ativo."}

    worker_id = f"worker-{os.getpid()}-{uuid.uuid4().hex[:6]}"
    with get_db_context() as db:
        pub_svc = PublisherService(db)
        claimed_posts = pub_svc.claim_due_scheduled_posts(worker_id=worker_id, limit=5)

        results = []
        for post in claimed_posts:
            res = pub_svc.execute_publish(post.id)
            results.append({"post_id": post.id, "result": res})

        return {"claimed": len(claimed_posts), "details": results}


@celery_app.task(name="app.tasks.publisher_tasks.task_reconcile_unknown")
def task_reconcile_unknown():
    """Reconciliação periódica de posts em estado UNKNOWN."""
    with get_db_context() as db:
        pub_svc = PublisherService(db)
        reconciled = pub_svc.reconcile_unknown_posts()
        logger.info(f"Posts reconciliados: {reconciled}")
        return {"reconciled": reconciled}
