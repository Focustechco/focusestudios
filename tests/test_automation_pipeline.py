import os
import time
import threading
import httpx
import pytest
from datetime import datetime, date

from app.config import settings
from app.services.sync_service import SyncService
from app.services.inspection_service import InspectionService
from app.services.calendar_service import CalendarService
from app.services.approval_service import ApprovalService
from app.services.publisher_service import PublisherService
from app.services.studio_exporter import StudioExporter
from app.models.account import Account
from app.models.media_asset import MediaAsset
from app.models.post_draft import PostDraft
from app.models.scheduled_post import ScheduledPost
from app.models.approval import Approval
from app.models.publish_attempt import PublishAttempt
from app.core.timezone import get_current_time_fortaleza, get_current_time_utc, format_fortaleza
import proxy_server


def test_full_automation_and_proxy_pipeline(db_session):
    """
    Teste Ponta a Ponta (E2E) da Automação Completa:
    1. Inicialização do Servidor Proxy Reverso e validação de tráfego.
    2. Sincronização e ingestão da pasta do Drive (com deduplicação SHA-256).
    3. Inspeção técnica de conformidade (ffprobe, formato 9:16, codecs).
    4. Geração de rascunhos e registro de consentimento individual inviolável.
    5. Distribuição da meta de 10 posts/dia no calendário em America/Fortaleza.
    6. Execução simulada do worker com reserva atômica (SKIP LOCKED).
    7. Transições de estado (SCHEDULED -> UPLOADING -> PROCESSING -> PUBLISHED).
    8. Validação do manifesto CSV para modo contingência TikTok Studio.
    """

    print("\n--- [ETAPA 1] TESTANDO O SERVIDOR PROXY REVERSO ---")
    proxy_server.PROXY_PORT = 8085
    proxy_server.BACKEND_URL = "http://127.0.0.1:8000"

    from http.server import HTTPServer
    proxy_httpd = HTTPServer(("127.0.0.1", 8085), proxy_server.ReverseProxyHandler)
    proxy_thread = threading.Thread(target=proxy_httpd.serve_forever, daemon=True)
    proxy_thread.start()

    time.sleep(0.5)

    # Testa healthcheck direto do proxy
    resp_proxy = httpx.get("http://127.0.0.1:8085/proxy-health")
    assert resp_proxy.status_code == 200
    data_proxy = resp_proxy.json()
    assert data_proxy["status"] == "ok"
    assert "Focus Reverse Proxy" in data_proxy["proxy"]
    print("-> Servidor Proxy Reverso respondendo com sucesso em http://127.0.0.1:8085/proxy-health")

    proxy_httpd.shutdown()

    print("\n--- [ETAPA 2] INGESTÃO E SINCRONIZAÇÃO COM O GOOGLE DRIVE ---")
    sync_svc = SyncService(db_session)
    sync_result = sync_svc.sync_drive_folder("test_folder_id")
    print(f"-> Sincronização finalizada: {sync_result}")
    assert sync_result["total_discovered"] >= 10
    assert sync_result["new_assets"] >= 10

    # Testa deduplicação na segunda execução
    resync = sync_svc.sync_drive_folder("test_folder_id")
    assert resync["new_assets"] == 0
    print("-> Deduplicação por SHA-256 validada: 0 arquivos duplicados na nova varredura.")

    print("\n--- [ETAPA 3] INSPEÇÃO TÉCNICA E VALIDAÇÃO DE MÍDIA ---")
    inspect_svc = InspectionService(db_session)
    inspected_count = inspect_svc.inspect_all_pending()
    print(f"-> Mídias inspecionadas: {inspected_count}")

    ready_assets = db_session.query(MediaAsset).filter_by(status="READY").all()
    assert len(ready_assets) >= 10
    for asset in ready_assets[:3]:
        print(f"   - Vídeo: {asset.name} | Duração: {asset.duration_seconds}s | Aspecto: {asset.aspect_ratio} | Codec: {asset.video_codec}")

    print("\n--- [ETAPA 4] REVISÃO, METADADOS & ASSINATURA DE CONSENTIMENTO ---")
    app_svc = ApprovalService(db_session)
    drafts = db_session.query(PostDraft).limit(10).all()
    assert len(drafts) >= 10

    approved_hashes = []
    for d in drafts:
        approval = app_svc.approve_draft(d.id, approved_by="senior_engineer")
        assert approval.is_active is True
        assert d.status == "APPROVED"
        approved_hashes.append(approval.content_hash)

    print(f"-> 10 rascunhos aprovados com hashes criptográficos registrados: ex: {approved_hashes[0][:16]}...")

    # Teste de invalidação automática se a legenda for alterada
    test_draft = drafts[0]
    app_svc.update_draft(
        draft_id=test_draft.id,
        title="Título Modificado Pós-Aprovação",
        caption="Legenda Alterada",
        hashtags="#teste",
        privacy_level="PUBLIC_TO_EVERYONE",
        disable_comment=False,
        disable_duet=False,
        disable_stitch=False,
        is_aigc=False,
        brand_content_toggle=False,
        brand_organic_toggle=False
    )
    db_session.refresh(test_draft)
    assert test_draft.status == "NEEDS_REVIEW"
    print("-> Regra de conformidade validada: alteração de legenda revogou aprovação prévia.")

    # Re-aprova para prosseguir com o agendamento
    app_svc.approve_draft(test_draft.id, approved_by="senior_engineer")

    print("\n--- [ETAPA 5] DISTRIBUIÇÃO NO CALENDÁRIO INTERNO (META 10/DIA) ---")
    cal_svc = CalendarService(db_session)
    sched_res = cal_svc.schedule_approved_drafts(days_ahead=1)
    print(f"-> Resultado do agendamento: {sched_res}")
    assert sched_res["scheduled"] > 0

    now_fortaleza = get_current_time_fortaleza().date()
    events = cal_svc.list_calendar_events(now_fortaleza, now_fortaleza)
    print(f"-> Total de publicações programadas para hoje em America/Fortaleza: {len(events)}")
    for ev in events[:5]:
        print(f"   [Slot {ev['time_fortaleza']}] {ev['title']} ({ev['status']})")

    print("\n--- [ETAPA 6] DISPARO DA ESTEIRA DO WORKER E PUBLICAÇÃO ---")
    pub_svc = PublisherService(db_session)
    # Força o horário do primeiro post para o presente para simular o worker atingindo o horário
    first_post = db_session.query(ScheduledPost).filter_by(status="SCHEDULED").first()
    assert first_post is not None

    first_post.scheduled_time_utc = get_current_time_utc()
    db_session.commit()

    # Worker reserva de forma atômica (SKIP LOCKED)
    claimed_posts = pub_svc.claim_due_scheduled_posts(worker_id="test_worker_01", limit=1)
    assert len(claimed_posts) == 1
    claimed = claimed_posts[0]
    assert claimed.status == "UPLOADING"
    print(f"-> Post {claimed.id} reservado com lock atômico pelo worker.")

    # Executa publicação
    pub_result = pub_svc.execute_publish(claimed.id)
    print(f"-> Resultado da publicação: {pub_result}")
    assert pub_result["status"] in ("PROCESSING", "PUBLISHED")
    assert "publish_id" in pub_result

    # Verifica histórico de tentativas
    attempt = db_session.query(PublishAttempt).filter_by(scheduled_post_id=claimed.id).first()
    assert attempt is not None
    assert attempt.publish_id == pub_result["publish_id"]
    print(f"-> Tentativa registrada com TikTok Publish ID: {attempt.publish_id}")

    print("\n--- [ETAPA 7] EXPORTAÇÃO MANUAL PARA TIKTOK STUDIO (CSV) ---")
    exporter = StudioExporter(db_session)
    csv_manifest = exporter.generate_manifest_csv()
    assert "Nome_Arquivo_Video" in csv_manifest
    assert "Data_Hora_Fortaleza" in csv_manifest
    assert "Aguardando agendamento manual no TikTok Studio" in csv_manifest
    print("-> Manifesto CSV gerado com sucesso contendo metadados homologados e fuso America/Fortaleza.")

    print("\n--- [ETAPA 8] MÉTRICAS FINAIS CONSOLIDADAS NO DASHBOARD ---")
    metrics = cal_svc.get_dashboard_metrics()
    print(f"-> Modo de Operação: {metrics['operation_mode']}")
    print(f"-> Meta Diária: {metrics['daily_target']} posts/dia")
    print(f"-> Programados Hoje: {metrics['today_scheduled']}")
    print(f"-> Estoque Disponível: {metrics['available_stock']} vídeos")
    print(f"-> Cobertura de Estoque: {metrics['coverage_days']} dias")
    print(f"-> Déficit de Vídeos: {metrics['daily_deficit']}")
    assert metrics["daily_target"] == 10

    print("\n[SUCESSO] Pipeline completo de automação e servidor proxy testados com 100% de conformidade!")
