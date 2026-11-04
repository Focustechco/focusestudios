import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine, get_db_context, init_db
from app.web.templates_env import templates

# Inicialização imediata de tabelas para compatibilidade total com cold starts do Vercel
init_db()
from app.web.routes import (
    inicio,
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
        try:
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

                # Garante que os arquivos físicos de vídeo no disco existam com seus vídeos específicos
                samples_dir = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "static", "video", "samples")
                )
                sample_preview_path = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "static", "video", "sample_preview.mp4")
                )
                all_assets = db.query(MediaAsset).all()
                for idx, a in enumerate(all_assets, 1):
                    # Determina o vídeo de amostra correspondente (1 a 15)
                    sample_idx = 1
                    if a.drive_file_id and "mock_file_" in a.drive_file_id:
                        try:
                            num = int(a.drive_file_id.split("mock_file_")[1].split("_")[0])
                            sample_idx = ((num - 1) % 15) + 1
                        except Exception:
                            sample_idx = ((idx - 1) % 15) + 1
                    else:
                        sample_idx = ((idx - 1) % 15) + 1

                    cand_sample = os.path.join(samples_dir, f"sample_{sample_idx:02d}.mp4")
                    chosen_src = cand_sample if os.path.exists(cand_sample) else sample_preview_path

                    target = a.local_storage_path or os.path.join(settings.STORAGE_DIR, "media", f"{a.drive_file_id}_{a.name}")
                    abs_p = os.path.abspath(target)
                    if os.path.exists(chosen_src):
                        if not os.path.exists(abs_p) or os.path.getsize(abs_p) < 10240:
                            os.makedirs(os.path.dirname(abs_p), exist_ok=True)
                            with open(chosen_src, "rb") as f_in:
                                specific_bytes = f_in.read()
                            with open(abs_p, "wb") as f_out:
                                f_out.write(specific_bytes + f"\n<!-- asset_id:{a.id} -->\n".encode("utf-8"))
                            if not a.local_storage_path:
                                a.local_storage_path = target
                db.commit()
        except Exception as e:
            print(f"[Lifespan Seed] Aviso ao executar seed DEMO: {e}")

    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Agente e Painel para Preparação e Publicação no TikTok via Google Drive",
    version="1.0.0",
    lifespan=lifespan
)

# Arquivos estáticos
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.isdir(static_dir):
    try:
        os.makedirs(static_dir, exist_ok=True)
    except Exception:
        pass
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Rotas
app.include_router(inicio.router)
app.include_router(dashboard.router)
app.include_router(connections.router)
app.include_router(library.router)
app.include_router(review.router)
app.include_router(calendar.router)
app.include_router(export_studio.router)
app.include_router(history.router)
app.include_router(settings_route.router)
app.include_router(api.router)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    ico_path = os.path.join(static_dir, "img", "favicon.ico")
    if os.path.exists(ico_path):
        return FileResponse(ico_path, media_type="image/x-icon")
    return FileResponse(os.path.join(static_dir, "img", "favicon-32x32.png"), media_type="image/png")


# Páginas legais (Termos de Serviço e Política de Privacidade para auditoria TikTok)


@app.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request):
    try:
        return templates.TemplateResponse(request=request, name="terms.html")
    except Exception:
        terms_path = os.path.join(os.path.dirname(__file__), "templates", "terms.html")
        if os.path.exists(terms_path):
            with open(terms_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        return HTMLResponse(content="<h1>Termos de Serviço</h1><p>Focus Publisher</p>")


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request):
    try:
        return templates.TemplateResponse(request=request, name="privacy.html")
    except Exception:
        privacy_path = os.path.join(os.path.dirname(__file__), "templates", "privacy.html")
        if os.path.exists(privacy_path):
            with open(privacy_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        return HTMLResponse(content="<h1>Política de Privacidade</h1><p>Focus Publisher</p>")


@app.get("/healthz")
def healthcheck():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "mode": settings.OPERATION_MODE,
        "timezone": settings.TIMEZONE
    }
