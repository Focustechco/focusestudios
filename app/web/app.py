import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine, get_db_context
from app.web.routes import (
    dashboard,
    connections,
    library,
    review,
    calendar,
    history,
    settings as settings_route,
    export_studio,
    api
)
from app.services.sync_service import SyncService
from app.services.inspection_service import InspectionService
from app.services.approval_service import ApprovalService
from app.services.calendar_service import CalendarService
from app.models.account import Account
from app.models.media_asset import MediaAsset


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializa tabelas
    Base.metadata.create_all(bind=engine)

    # Seed inicial no modo DEMO se o banco estiver vazio
    if settings.OPERATION_MODE == "DEMO":
        with get_db_context() as db:
            # Garante conta TikTok DEMO
            acc = db.query(Account).filter_by(open_id="demo_open_id").first()
            if not acc:
                acc = Account(
                    open_id="demo_open_id",
                    username="@focustech_demo",
                    display_name="Focus Tech Oficial (DEMO)",
                    avatar_url="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=150",
                    privacy_options="PUBLIC_TO_EVERYONE,MUTUAL_FOLLOW_FRIENDS,SELF_ONLY",
                    is_eligible=True,
                    eligibility_notes="Conta simulada para demonstração e testes."
                )
                acc.access_token = "mock_access_token_demo"
                acc.refresh_token = "mock_refresh_token_demo"
                db.add(acc)
                db.commit()

            # Se não houver vídeos, executa sincronização inicial de exemplo
            asset_count = db.query(MediaAsset).count()
            if asset_count == 0:
                sync_svc = SyncService(db)
                sync_svc.sync_drive_folder(settings.GOOGLE_DRIVE_FOLDER_ID)
                inspect_svc = InspectionService(db)
                inspect_svc.inspect_all_pending()

                # Aprova automaticamente alguns rascunhos iniciais e distribui no calendário
                app_svc = ApprovalService(db)
                from app.models.post_draft import PostDraft
                drafts = db.query(PostDraft).limit(10).all()
                for d in drafts:
                    try:
                        app_svc.approve_draft(d.id, approved_by="setup_demo")
                    except Exception:
                        pass

                cal_svc = CalendarService(db)
                cal_svc.schedule_approved_drafts(days_ahead=1)

    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Agente e Painel para Preparação e Publicação no TikTok via Google Drive",
    version="1.0.0",
    lifespan=lifespan
)

# Arquivos estáticos
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Rotas
app.include_router(dashboard.router)
app.include_router(connections.router)
app.include_router(library.router)
app.include_router(review.router)
app.include_router(calendar.router)
app.include_router(export_studio.router)
app.include_router(history.router)
app.include_router(settings_route.router)
app.include_router(api.router)


@app.get("/healthz")
def healthcheck():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "mode": settings.OPERATION_MODE,
        "timezone": settings.TIMEZONE
    }
