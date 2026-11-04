from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.config import settings
from app.services.calendar_service import CalendarService
from app.models.scheduled_post import ScheduledPost
from app.core.timezone import get_current_time_fortaleza, format_fortaleza

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


@router.get("/dashboard", response_class=HTMLResponse)
@router.get("/metrics", response_class=HTMLResponse)
def get_dashboard(request: Request, db: Session = Depends(get_db)):
    cal_svc = CalendarService(db)
    metrics = cal_svc.get_dashboard_metrics()

    # Próximas publicações agendadas
    posts = db.query(ScheduledPost).filter(
        ScheduledPost.status.in_(["SCHEDULED", "UPLOADING", "PROCESSING", "PUBLISHED"])
    ).order_by(ScheduledPost.scheduled_time_utc.asc()).limit(10).all()

    upcoming_posts = []
    for p in posts:
        upcoming_posts.append({
            "id": p.id,
            "title": p.post_draft.title if p.post_draft else "Sem título",
            "caption": p.post_draft.caption if p.post_draft else "",
            "privacy": p.post_draft.privacy_level if p.post_draft else "SELF_ONLY",
            "status": p.status,
            "time_fortaleza": format_fortaleza(p.scheduled_time_utc)
        })

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "title": "Dashboard",
            "active_page": "dashboard",
            "operation_mode": settings.OPERATION_MODE,
            "timezone": settings.TIMEZONE,
            "metrics": metrics,
            "upcoming_posts": upcoming_posts
        }
    )
