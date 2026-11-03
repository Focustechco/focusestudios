from app.services.calendar_service import CalendarService
from app.models.media_asset import MediaAsset
from app.config import settings


def test_stock_and_daily_deficit_calculation(db_session):
    cal_svc = CalendarService(db_session)
    
    # Estado inicial: sem ativos de mídia
    metrics_initial = cal_svc.get_dashboard_metrics()
    assert metrics_initial["available_stock"] == 0
    assert metrics_initial["coverage_days"] == 0.0
    assert metrics_initial["daily_deficit"] == settings.DAILY_POST_TARGET

    # Adicionar 25 ativos no banco
    for i in range(25):
        asset = MediaAsset(
            drive_file_id=f"stock_file_{i:03d}",
            name=f"video_stock_{i}.mp4",
            sha256_hash=f"hash_stock_{i:03d}",
            file_size_bytes=5000,
            status="READY"
        )
        db_session.add(asset)
    db_session.commit()

    metrics_updated = cal_svc.get_dashboard_metrics()
    assert metrics_updated["available_stock"] == 25
    # Com 25 vídeos e meta diária de 10: cobertura = 2.5 dias
    assert metrics_updated["coverage_days"] == 2.5
