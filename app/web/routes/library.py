from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.media_asset import MediaAsset

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


@router.get("/library", response_class=HTMLResponse)
def get_library(request: Request, db: Session = Depends(get_db)):
    assets = db.query(MediaAsset).order_by(MediaAsset.created_at.desc()).all()

    return templates.TemplateResponse(
        "library.html",
        {
            "request": request,
            "title": "Biblioteca de Mídia",
            "active_page": "library",
            "operation_mode": settings.OPERATION_MODE,
            "timezone": settings.TIMEZONE,
            "assets": assets
        }
    )
