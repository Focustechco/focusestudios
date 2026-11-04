from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings

from app.web.templates_env import templates

router = APIRouter()


@router.get("/settings", response_class=HTMLResponse)
def get_settings(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "title": "Configurações",
            "active_page": "settings",
            "operation_mode": settings.OPERATION_MODE,
            "timezone": settings.TIMEZONE,
            "settings": settings
        }
    )
