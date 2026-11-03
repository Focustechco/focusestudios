import os
import time
import logging
from app.tasks.celery_app import celery_app
from app.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.maintenance_tasks.task_cleanup_media")
def task_cleanup_media():
    """Limpeza periódica de arquivos temporários com retenção superior a TEMP_CLEANUP_DAYS."""
    media_dir = os.path.join(settings.STORAGE_DIR, "media")
    if not os.path.exists(media_dir):
        return {"deleted": 0}

    now = time.time()
    retention_seconds = settings.TEMP_CLEANUP_DAYS * 86400
    deleted_count = 0

    for fname in os.listdir(media_dir):
        fpath = os.path.join(media_dir, fname)
        if os.path.isfile(fpath):
            if now - os.path.getmtime(fpath) > retention_seconds:
                try:
                    os.remove(fpath)
                    deleted_count += 1
                except Exception as ex:
                    logger.warning(f"Erro ao remover arquivo temporário {fpath}: {str(ex)}")

    logger.info(f"Limpeza de mídia temporária finalizada: {deleted_count} arquivos removidos.")
    return {"deleted": deleted_count}
