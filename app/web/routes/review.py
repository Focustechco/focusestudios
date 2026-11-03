from typing import Optional
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.post_draft import PostDraft
from app.models.account import Account

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


@router.get("/review", response_class=HTMLResponse)
def get_review(
    request: Request,
    draft_id: Optional[str] = Query(None),
    asset_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    drafts = db.query(PostDraft).order_by(PostDraft.created_at.desc()).all()
    selected_draft = None

    if draft_id:
        selected_draft = db.query(PostDraft).filter_by(id=draft_id).first()
    elif asset_id:
        selected_draft = db.query(PostDraft).filter_by(media_asset_id=asset_id).first()
    elif drafts:
        selected_draft = drafts[0]

    account = db.query(Account).filter_by(is_active=True).first()
    privacy_options = ["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "FOLLOWER_OF_CREATOR", "SELF_ONLY"]
    if account and account.privacy_options:
        privacy_options = [opt.strip() for opt in account.privacy_options.split(",") if opt.strip()]

    return templates.TemplateResponse(
        "review.html",
        {
            "request": request,
            "title": "Revisão & Consentimento",
            "active_page": "review",
            "operation_mode": settings.OPERATION_MODE,
            "timezone": settings.TIMEZONE,
            "drafts": drafts,
            "selected_draft": selected_draft,
            "privacy_options": privacy_options
        }
    )
