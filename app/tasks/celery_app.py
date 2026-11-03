import os
from celery import Celery
from app.config import settings

celery_app = Celery(
    "focus_publisher",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.sync_tasks",
        "app.tasks.publisher_tasks",
        "app.tasks.maintenance_tasks"
    ]
)

celery_app.conf.update(
    timezone=settings.TIMEZONE,
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    broker_connection_retry_on_startup=True
)

# Celery Beat Periodic Schedule
celery_app.conf.beat_schedule = {
    # 1. Verifica e dispara publicações no minuto programado
    "check-and-publish-due-posts-every-minute": {
        "task": "app.tasks.publisher_tasks.task_check_and_publish_due",
        "schedule": 60.0,
    },
    # 2. Sincroniza a pasta do Google Drive periodicamente
    "sync-drive-sources-interval": {
        "task": "app.tasks.sync_tasks.task_sync_primary_drive",
        "schedule": float(settings.DRIVE_SYNC_INTERVAL_MINUTES * 60),
    },
    # 3. Reconciliação de posts em quarentena / timeout (UNKNOWN)
    "reconcile-unknown-posts-every-5-minutes": {
        "task": "app.tasks.publisher_tasks.task_reconcile_unknown",
        "schedule": 300.0,
    },
    # 4. Limpeza de arquivos temporários antigos
    "cleanup-temporary-media-daily": {
        "task": "app.tasks.maintenance_tasks.task_cleanup_media",
        "schedule": 86400.0,
    }
}
