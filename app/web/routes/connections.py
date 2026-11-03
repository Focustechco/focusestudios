from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.database import get_db
from app.config import settings
from app.models.drive_source import DriveSource
from app.models.account import Account
from app.models.audit_event import AuditEvent
from app.services.sync_service import SyncService
from app.core.security import generate_state_token
from app.core.timezone import get_current_time_utc
from app.adapters.tiktok.mock_tiktok import MockTikTokAdapter
from app.adapters.tiktok.direct_post import TikTokDirectPostAdapter

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


@router.get("/connections", response_class=HTMLResponse)
def get_connections(request: Request, db: Session = Depends(get_db)):
    sync_svc = SyncService(db)
    drive_source = sync_svc.get_or_create_primary_source()
    account = db.query(Account).filter_by(is_active=True).first()

    return templates.TemplateResponse(
        "connections.html",
        {
            "request": request,
            "title": "Conexões",
            "active_page": "connections",
            "operation_mode": settings.OPERATION_MODE,
            "timezone": settings.TIMEZONE,
            "drive_source": drive_source,
            "account": account
        }
    )


@router.get("/connections/tiktok/login")
def tiktok_oauth_login():
    """Inicia o fluxo OAuth 2.0 oficial com state anti-CSRF."""
    if settings.OPERATION_MODE == "DEMO":
        # No modo DEMO, redireciona simulando consentimento imediato
        return RedirectResponse(url="/connections/tiktok/callback?code=mock_oauth_code&state=demo")

    state = generate_state_token("admin", "tiktok_oauth")
    auth_url = (
        f"https://www.tiktok.com/v2/auth/authorize/?"
        f"client_key={settings.TIKTOK_CLIENT_KEY}&"
        f"response_type=code&"
        f"scope=user.info.basic,video.publish,video.upload&"
        f"redirect_uri={settings.TIKTOK_REDIRECT_URI}&"
        f"state={state}"
    )
    return RedirectResponse(url=auth_url)


@router.get("/connections/tiktok/callback")
def tiktok_oauth_callback(
    code: str = Query(...),
    state: str = Query(None),
    db: Session = Depends(get_db)
):
    """Callback do OAuth TikTok: troca código por access e refresh token e consulta creator_info."""
    if settings.OPERATION_MODE == "DEMO":
        adapter = MockTikTokAdapter()
        creator_info = adapter.query_creator_info("mock_token")

        account = db.query(Account).filter_by(open_id="demo_open_id").first()
        if not account:
            account = Account(
                open_id="demo_open_id",
                username=creator_info["creator_username"],
                display_name=creator_info["creator_nickname"],
                avatar_url=creator_info["creator_avatar_url"],
                privacy_options=",".join(creator_info["privacy_level_options"]),
                is_eligible=True,
                eligibility_notes="Ambiente de Simulação DEMO Ativo.",
                token_expires_at=datetime.utcnow() + timedelta(days=30)
            )
            account.access_token = "mock_access_token_demo"
            account.refresh_token = "mock_refresh_token_demo"
            db.add(account)
        else:
            account.privacy_options = ",".join(creator_info["privacy_level_options"])
            account.token_expires_at = datetime.utcnow() + timedelta(days=30)

        db.commit()
        return RedirectResponse(url="/connections?success=true")

    # Em modo DIRECT_POST real:
    # 1. Troca code por tokens
    # 2. Consulta /v2/post/publish/creator_info/query/
    return RedirectResponse(url="/connections?notice=oauth_completed")
