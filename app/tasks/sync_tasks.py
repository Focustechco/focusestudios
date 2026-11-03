import logging
from app.tasks.celery_app import celery_app
from app.database import get_db_context
from app.services.sync_service import SyncService
from app.services.inspection_service import InspectionService
from app.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.sync_tasks.task_sync_primary_drive")
def task_sync_primary_drive():
    """Tarefa assíncrona de sincronização periódica da pasta do Drive."""
    logger.info("Iniciando sincronização com Google Drive...")
    with get_db_context() as db:
        sync_svc = SyncService(db)
        result = sync_svc.sync_drive_folder(settings.GOOGLE_DRIVE_FOLDER_ID)
        logger.info(f"Sincronização concluída: {result}")

        # Inspeciona automaticamente mídias recém-descobertas
        inspect_svc = InspectionService(db)
        inspected_count = inspect_svc.inspect_all_pending()
        logger.info(f"Mídias inspecionadas: {inspected_count}")

    return result
