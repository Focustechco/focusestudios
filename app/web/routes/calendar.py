from typing import Optional
from datetime import timedelta
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.services.calendar_service import CalendarService
from app.core.timezone import get_current_time_fortaleza
from app.web.templates_env import templates

router = APIRouter()


@router.get("/calendar", response_class=HTMLResponse)
def get_calendar(
    request: Request,
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    view: str = Query("grid"),
    db: Session = Depends(get_db)
):
    cal_svc = CalendarService(db)
    now_fortaleza = get_current_time_fortaleza()

    current_year = year or now_fortaleza.year
    current_month = month or now_fortaleza.month

    if current_month < 1 or current_month > 12:
        current_month = now_fortaleza.month

    calendar_data = cal_svc.get_monthly_calendar_data(current_year, current_month)

    # Eventos para a visão em tabela (janela de 15 dias)
    today_date = now_fortaleza.date()
    events = cal_svc.list_calendar_events(
        start_date=today_date,
        end_date=today_date + timedelta(days=15)
    )

    return templates.TemplateResponse(
        request=request,
        name="calendar.html",
        context={
            "title": "Calendário de Publicações",
            "active_page": "calendar",
            "operation_mode": settings.OPERATION_MODE,
            "timezone": settings.TIMEZONE,
            "events": events,
            "calendar_data": calendar_data,
            "view_mode": view,
            "daily_target": settings.DAILY_POST_TARGET
        }
    )

