from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.services.calendar_service import CalendarService
from app.models.scheduled_post import ScheduledPost
from app.models.media_asset import MediaAsset
from app.models.post_draft import PostDraft
from app.core.timezone import get_current_time_fortaleza, format_fortaleza, to_utc
from app.web.templates_env import templates

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
@router.get("/metrics", response_class=HTMLResponse)
def get_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    cal_svc = CalendarService(db)
    metrics = cal_svc.get_dashboard_metrics()

    now_fortaleza = get_current_time_fortaleza()
    today = now_fortaleza.date()

    # 1. Gráfico 1: Cadência Diária de Publicações vs Meta (14 dias: -6 até +7 dias)
    daily_labels = []
    published_series = []
    scheduled_series = []
    target_series = []

    for offset in range(-6, 8):
        day_date = today + timedelta(days=offset)
        start_utc = to_utc(datetime.combine(day_date, datetime.min.time()))
        end_utc = to_utc(datetime.combine(day_date, datetime.max.time()))

        posts_day = db.query(ScheduledPost).filter(
            ScheduledPost.scheduled_time_utc >= start_utc,
            ScheduledPost.scheduled_time_utc <= end_utc
        ).all()

        pub_cnt = sum(1 for p in posts_day if p.status == "PUBLISHED")
        sch_cnt = sum(1 for p in posts_day if p.status in ["SCHEDULED", "UPLOADING", "PROCESSING"])

        is_today_str = " (Hoje)" if day_date == today else ""
        daily_labels.append(f"{day_date.strftime('%d/%m')}{is_today_str}")
        published_series.append(pub_cnt)
        scheduled_series.append(sch_cnt)
        target_series.append(settings.DAILY_POST_TARGET)

    chart_daily = {
        "labels": daily_labels,
        "published": published_series,
        "scheduled": scheduled_series,
        "target": target_series,
        "daily_target": settings.DAILY_POST_TARGET
    }

    # 2. Gráfico 2: Pipeline Operacional & Saúde do Conteúdo (Dados Reais)
    total_assets = db.query(MediaAsset).count()
    drafts_review = db.query(PostDraft).filter(PostDraft.status.in_(["DRAFT", "NEEDS_REVIEW"])).count()
    drafts_approved = db.query(PostDraft).filter(PostDraft.status == "APPROVED").count()
    posts_scheduled = db.query(ScheduledPost).filter(ScheduledPost.status.in_(["SCHEDULED", "UPLOADING", "PROCESSING"])).count()
    posts_published = db.query(ScheduledPost).filter(ScheduledPost.status == "PUBLISHED").count()
    posts_failed = db.query(ScheduledPost).filter(ScheduledPost.status.in_(["FAILED", "UNKNOWN"])).count()

    # Mídias brutas sem rascunho ativo
    assets_raw_count = db.query(MediaAsset).filter(~MediaAsset.post_drafts.any()).count()

    chart_pipeline = {
        "labels": [
            "Mídias no Estoque",
            "Em Revisão",
            "Aprovados",
            "Agendados",
            "Publicados",
            "Falhas / Ação"
        ],
        "data": [
            assets_raw_count,
            drafts_review,
            drafts_approved,
            posts_scheduled,
            posts_published,
            posts_failed
        ],
        "colors": [
            "#3b82f6",
            "#f59e0b",
            "#8b5cf6",
            "#ff6600",
            "#10b981",
            "#ef4444"
        ],
        "total_items": total_assets + posts_published
    }

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
            "title": "Métricas & Performance",
            "active_page": "dashboard",
            "operation_mode": settings.OPERATION_MODE,
            "timezone": settings.TIMEZONE,
            "metrics": metrics,
            "upcoming_posts": upcoming_posts,
            "chart_daily": chart_daily,
            "chart_pipeline": chart_pipeline
        }
    )

