from datetime import timedelta
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.services.calendar_service import CalendarService
from app.core.timezone import get_current_time_fortaleza
from app.web.templates_env import templates

router = APIRouter()


@router.get("/calendar", response_class=HTMLResponse)
def get_calendar(request: Request, db: Session = Depends(get_db)):
    cal_svc = CalendarService(db)
    now_fortaleza = get_current_time_fortaleza().date()
    events = cal_svc.list_calendar_events(
        start_date=now_fortaleza,
        end_date=now_fortaleza + timedelta(days=7)
    )

    return templates.TemplateResponse(
        request=request,
        name="calendar.html",
        context={
            "title": "Calendário Interno",
            "active_page": "calendar",
            "operation_mode": settings.OPERATION_MODE,
            "timezone": settings.TIMEZONE,
            "events": events
        }
    )
