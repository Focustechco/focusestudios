from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


@router.get("/settings", response_class=HTMLResponse)
def get_settings(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "title": "Configurações",
            "active_page": "settings",
            "operation_mode": settings.OPERATION_MODE,
            "timezone": settings.TIMEZONE,
            "settings": settings
        }
    )
