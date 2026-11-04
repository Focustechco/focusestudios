import logging
import urllib.parse
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

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


@router.get("/connections", response_class=HTMLResponse)
def get_connections(request: Request, db: Session = Depends(get_db)):
    sync_svc = SyncService(db)
    drive_source = sync_svc.get_or_create_primary_source()
    account = db.query(Account).filter_by(is_active=True).first()

    return templates.TemplateResponse(
        request=request,
        name="connections.html",
        context={
            "title": "Conexões",
            "active_page": "connections",
            "operation_mode": settings.OPERATION_MODE,
            "timezone": settings.TIMEZONE,
            "drive_source": drive_source,
            "account": account
        }
    )


import secrets
import hashlib

PKCE_STORE = {}


@router.get("/connections/tiktok/login")
def tiktok_oauth_login():
    """Inicia o fluxo OAuth 2.0 oficial com state anti-CSRF e PKCE (S256)."""
    if settings.OPERATION_MODE == "DEMO":
        # No modo DEMO, redireciona simulando consentimento imediato
        return RedirectResponse(url="/connections/tiktok/callback?code=mock_oauth_code&state=demo")

    state = generate_state_token("admin", "tiktok_oauth")
    # Geração de PKCE oficial conforme especificação TikTok
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).hexdigest()
    PKCE_STORE[state] = code_verifier

    auth_url = (
        f"https://www.tiktok.com/v2/auth/authorize/?"
        f"client_key={settings.TIKTOK_CLIENT_KEY}&"
        f"response_type=code&"
        f"scope=user.info.basic,video.publish&"
        f"redirect_uri={settings.TIKTOK_REDIRECT_URI}&"
        f"state={state}&"
        f"code_challenge={code_challenge}&"
        f"code_challenge_method=S256"
    )
    response = RedirectResponse(url=auth_url)
    response.set_cookie("pkce_verifier", code_verifier, max_age=600, httponly=True)
    return response


@router.get("/connections/tiktok/callback")
def tiktok_oauth_callback(
    request: Request,
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

    # Em modo DIRECT_POST real com PKCE:
    try:
        code_verifier = PKCE_STORE.pop(state, None) or request.cookies.get("pkce_verifier") or ""
        adapter = TikTokDirectPostAdapter()
        token_data = adapter.exchange_code_for_token(
            code=code,
            redirect_uri=settings.TIKTOK_REDIRECT_URI,
            code_verifier=code_verifier
        )

        access_token = token_data.get("access_token", "")
        refresh_token = token_data.get("refresh_token", "")
        open_id = token_data.get("open_id", "")
        expires_in = int(token_data.get("expires_in") or 86400)
        refresh_expires_in = int(token_data.get("refresh_expires_in") or 86400 * 30)

        # Consulta dados reais e limites da conta
        creator_info = adapter.query_creator_info(access_token)
        privacy_opts = ",".join(creator_info.get("privacy_level_options", []))

        account = db.query(Account).filter_by(open_id=open_id).first() if open_id else None
        if not account:
            account = db.query(Account).filter_by(is_active=True).first()

        if not account:
            account = Account(
                open_id=open_id or f"tiktok_{secrets.token_hex(6)}",
                username=creator_info.get("creator_username") or "@tiktok_creator"
            )
            db.add(account)

        account.open_id = open_id or account.open_id
        account.access_token = access_token
        account.refresh_token = refresh_token
        account.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        account.refresh_expires_at = datetime.utcnow() + timedelta(seconds=refresh_expires_in)
        account.username = creator_info.get("creator_username") or "@tiktok_creator"
        account.display_name = creator_info.get("creator_nickname") or "TikTok Creator"
        account.avatar_url = creator_info.get("creator_avatar_url") or ""
        account.privacy_options = privacy_opts
        account.comment_disabled = bool(creator_info.get("comment_disabled", False))
        account.duet_disabled = bool(creator_info.get("duet_disabled", False))
        account.stitch_disabled = bool(creator_info.get("stitch_disabled", False))
        account.scopes = token_data.get("scope") or "user.info.basic,video.publish"
        account.is_eligible = True
        account.is_active = True
        account.eligibility_notes = "Conta oficial TikTok vinculada via Direct Post v2 (PKCE ativo)."
        db.flush()

        # Desativa outras contas para garantir apenas a conta vinculada ativa
        db.query(Account).filter(Account.id != account.id).update({"is_active": False})
        db.flush()

        audit = AuditEvent(
            action="TIKTOK_ACCOUNT_CONNECTED",
            entity_type="account",
            entity_id=account.id,
            user_or_system="oauth",
            details=f"Conta {account.username} vinculada com sucesso. Opções de privacidade: {privacy_opts}"
        )
        db.add(audit)
        db.commit()

        return RedirectResponse(url="/connections?success=true", status_code=303)
    except Exception as e:
        logger.error(f"Erro ao processar callback do TikTok: {e}", exc_info=True)
        return RedirectResponse(url=f"/connections?error={urllib.parse.quote(str(e))}", status_code=303)
