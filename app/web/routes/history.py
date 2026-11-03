from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.publish_attempt import PublishAttempt
from app.models.audit_event import AuditEvent

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


@router.get("/history", response_class=HTMLResponse)
def get_history(request: Request, db: Session = Depends(get_db)):
    attempts = db.query(PublishAttempt).order_by(PublishAttempt.started_at.desc()).limit(50).all()
    audit_events = db.query(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(50).all()

    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={
            "title": "Histórico & Auditoria",
            "active_page": "history",
            "operation_mode": settings.OPERATION_MODE,
            "timezone": settings.TIMEZONE,
            "attempts": attempts,
            "audit_events": audit_events
        }
    )
