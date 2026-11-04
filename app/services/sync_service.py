import os
import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime

from app.config import settings
from app.models.drive_source import DriveSource
from app.models.media_asset import MediaAsset
from app.models.audit_event import AuditEvent
from app.adapters.drive.mock_drive import MockDriveAdapter
from app.adapters.drive.google_drive import GoogleDriveAdapter
from app.core.timezone import get_current_time_utc

logger = logging.getLogger(__name__)


class SyncService:
    def __init__(self, db: Session):
        self.db = db
        if settings.OPERATION_MODE == "DEMO":
            self.drive_adapter = MockDriveAdapter()
        else:
            self.drive_adapter = GoogleDriveAdapter()

    def get_or_create_primary_source(self) -> DriveSource:
        source = self.db.query(DriveSource).filter_by(folder_id=settings.GOOGLE_DRIVE_FOLDER_ID).first()
        if not source:
            source = DriveSource(
                folder_id=settings.GOOGLE_DRIVE_FOLDER_ID,
                name="Pasta Principal Google Drive",
                include_subfolders=settings.DRIVE_INCLUDE_SUBFOLDERS,
                sync_interval_minutes=settings.DRIVE_SYNC_INTERVAL_MINUTES,
                is_active=True
            )
            self.db.add(source)
            self.db.commit()
            self.db.refresh(source)
        return source

    def sync_drive_folder(self, folder_id: str) -> Dict[str, Any]:
        """
        Sincroniza os arquivos da pasta do Google Drive com paginação completa.
        Detecta duplicatas por SHA-256 e MD5.
        """
        source = self.get_or_create_primary_source()
        page_token = None
        new_assets = 0
        duplicates_skipped = 0
        total_discovered = 0

        while True:
            files, next_page = self.drive_adapter.list_files(
                folder_id=folder_id,
                page_token=page_token,
                include_subfolders=source.include_subfolders
            )

            for f_meta in files:
                total_discovered += 1
                # 1. Verificar se é documento proprietário não binário
                if f_meta.mime_type and f_meta.mime_type.startswith("application/vnd.google-apps."):
                    continue

                # 2. Verificar se já existe pelo drive_file_id
                existing_by_id = self.db.query(MediaAsset).filter_by(drive_file_id=f_meta.file_id).first()
                if existing_by_id:
                    continue

                # 2. Baixar para armazenamento local temporário e calcular SHA-256
                local_path = os.path.join(settings.STORAGE_DIR, "media", f"{f_meta.file_id}_{f_meta.name}")
                sha256_hash = self.drive_adapter.download_file(f_meta.file_id, local_path)

                # 3. Verificar duplicata cross-file pelo hash SHA-256
                existing_by_hash = self.db.query(MediaAsset).filter_by(sha256_hash=sha256_hash).first()
                if existing_by_hash:
                    duplicates_skipped += 1
                    # Remove o arquivo temporário baixado para poupar espaço
                    if os.path.exists(local_path):
                        os.remove(local_path)
                    continue

                # Cria o novo ativo de mídia
                asset = MediaAsset(
                    drive_source_id=source.id,
                    drive_file_id=f_meta.file_id,
                    name=f_meta.name,
                    mime_type=f_meta.mime_type,
                    file_size_bytes=f_meta.size_bytes,
                    sha256_hash=sha256_hash,
                    md5_checksum=f_meta.md5_checksum,
                    local_storage_path=local_path,
                    status="DISCOVERED"
                )
                self.db.add(asset)
                new_assets += 1

            page_token = next_page
            if not page_token:
                break

        source.last_synced_at = get_current_time_utc()
        
        # Auditoria
        audit = AuditEvent(
            action="DRIVE_SYNC_COMPLETED",
            entity_type="drive_source",
            entity_id=source.id,
            user_or_system="worker",
            details=f"Descobertos: {total_discovered}, Novos: {new_assets}, Duplicatas ignoradas: {duplicates_skipped}"
        )
        self.db.add(audit)
        self.db.commit()

        return {
            "total_discovered": total_discovered,
            "new_assets": new_assets,
            "duplicates_skipped": duplicates_skipped
        }
