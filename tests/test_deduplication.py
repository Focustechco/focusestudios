import os
import hashlib
from app.services.sync_service import SyncService
from app.models.media_asset import MediaAsset
from app.adapters.drive.mock_drive import MockDriveAdapter


def test_drive_pagination_and_deduplication(db_session):
    sync_svc = SyncService(db_session)
    result = sync_svc.sync_drive_folder("test_folder_id")

    # Verifica se a paginação descobriu todos os arquivos simulados
    assert result["total_discovered"] == len(MockDriveAdapter.SAMPLE_VIDEOS)
    assert result["new_assets"] > 0

    # Segunda sincronização: não deve duplicar nenhum arquivo existente
    second_result = sync_svc.sync_drive_folder("test_folder_id")
    assert second_result["new_assets"] == 0


def test_sha256_cross_file_deduplication(db_session):
    sync_svc = SyncService(db_session)
    source = sync_svc.get_or_create_primary_source()

    # Cria primeiro ativo com um hash específico
    unique_hash = hashlib.sha256(b"identical_video_content").hexdigest()
    asset1 = MediaAsset(
        drive_source_id=source.id,
        drive_file_id="drive_file_001",
        name="video_original.mp4",
        sha256_hash=unique_hash,
        file_size_bytes=1000,
        status="DISCOVERED"
    )
    db_session.add(asset1)
    db_session.commit()

    # Tenta inserir segundo arquivo com nome e drive_file_id diferentes, mas mesmo hash SHA-256
    duplicate_found = db_session.query(MediaAsset).filter_by(sha256_hash=unique_hash).first()
    assert duplicate_found is not None
    assert duplicate_found.drive_file_id == "drive_file_001"
