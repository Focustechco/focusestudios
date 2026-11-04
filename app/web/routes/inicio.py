import os
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.config import settings
from app.models.media_asset import MediaAsset
from app.models.post_draft import PostDraft
from app.models.scheduled_post import ScheduledPost
from app.models.account import Account
from app.models.audit_event import AuditEvent
from app.core.timezone import (
    get_current_time_fortaleza,
    format_fortaleza,
    to_utc,
    to_fortaleza
)
from app.web.templates_env import templates

router = APIRouter()


def format_duration(seconds: float | None) -> str:
    if not seconds or seconds <= 0:
        return "00:00"
    total_sec = int(round(seconds))
    mins = total_sec // 60
    secs = total_sec % 60
    return f"{mins:02d}:{secs:02d}"


@router.get("/", response_class=HTMLResponse)
@router.get("/inicio", response_class=HTMLResponse)
def get_inicio(request: Request, db: Session = Depends(get_db)):
    now_fortaleza = get_current_time_fortaleza()
    today = now_fortaleza.date()

    # 1. Indicador: Vídeos na fila (rascunhos aguardando processamento, revisão ou publicação)
    try:
        videos_in_queue = db.query(PostDraft).filter(
            PostDraft.status != "PUBLISHED"
        ).count()
        if videos_in_queue == 0:
            videos_in_queue = db.query(MediaAsset).count()
    except Exception:
        videos_in_queue = 0

    # 2. Indicador: Publicações hoje (previstas para a data atual no fuso Fortaleza)
    try:
        start_of_day_utc = to_utc(datetime.combine(today, datetime.min.time()))
        end_of_day_utc = to_utc(datetime.combine(today, datetime.max.time()))

        today_scheduled = db.query(ScheduledPost).filter(
            ScheduledPost.scheduled_time_utc >= start_of_day_utc,
            ScheduledPost.scheduled_time_utc <= end_of_day_utc,
            ScheduledPost.status.in_(["SCHEDULED", "UPLOADING", "PROCESSING", "PUBLISHED"])
        ).count()
    except Exception:
        today_scheduled = 0

    # 3. Indicador: Canais conectados
    connected_channels = 0
    if settings.GOOGLE_DRIVE_FOLDER_ID:
        connected_channels += 1

    try:
        active_tiktok = db.query(Account).filter_by(is_active=True).first()
        if active_tiktok and active_tiktok.access_token:
            connected_channels += 1
    except Exception:
        pass

    # Projetos recentes (limite 6)
    recent_projects = []
    try:
        drafts = db.query(PostDraft).order_by(
            PostDraft.updated_at.desc(),
            PostDraft.created_at.desc()
        ).limit(6).all()

        for d in drafts:
            asset = d.media_asset
            duration_str = format_duration(asset.duration_seconds if asset else 0)
            recent_projects.append({
                "id": d.id,
                "asset_id": d.media_asset_id,
                "title": d.title or (asset.name if asset else "Vídeo sem título"),
                "file_name": asset.name if asset else "video.mp4",
                "duration": duration_str,
                "duration_raw": asset.duration_seconds if asset else 0,
                "aspect_ratio": asset.aspect_ratio if asset else "9:16",
                "resolution": f"{asset.width}x{asset.height}" if (asset and asset.width) else "1080x1920",
                "status": d.status,
                "updated_at": format_fortaleza(d.updated_at or d.created_at),
                "updated_time_short": to_fortaleza(d.updated_at or d.created_at).strftime("%d/%m %H:%M")
            })
    except Exception:
        recent_projects = []

    # Próximas publicações reais (limite 4)
    upcoming_posts = []
    try:
        posts = db.query(ScheduledPost).filter(
            ScheduledPost.status.in_(["SCHEDULED", "UPLOADING", "PROCESSING", "PUBLISHED"])
        ).order_by(ScheduledPost.scheduled_time_utc.asc()).limit(4).all()

        for p in posts:
            post_time_fortaleza = to_fortaleza(p.scheduled_time_utc)
            is_today = post_time_fortaleza.date() == today
            is_tomorrow = post_time_fortaleza.date() == (today + timedelta(days=1))
            if is_today:
                date_label = f"Hoje às {post_time_fortaleza.strftime('%H:%M')}"
            elif is_tomorrow:
                date_label = f"Amanhã às {post_time_fortaleza.strftime('%H:%M')}"
            else:
                date_label = post_time_fortaleza.strftime("%d/%m às %H:%M")

            upcoming_posts.append({
                "id": p.id,
                "title": p.post_draft.title if p.post_draft else "Sem título",
                "channel_name": p.account.username if p.account else "@focustech",
                "channel_icon": "tiktok",
                "date_label": date_label,
                "status": p.status
            })
    except Exception:
        upcoming_posts = []

    # Notificações reais da central (últimos eventos de auditoria)
    notifications = []
    try:
        audit_events = db.query(AuditEvent).order_by(
            AuditEvent.created_at.desc()
        ).limit(5).all()

        for ev in audit_events:
            notifications.append({
                "id": ev.id,
                "action": ev.action,
                "details": ev.details or ev.action,
                "time": format_fortaleza(ev.created_at)
            })
    except Exception:
        notifications = []

    return templates.TemplateResponse(
        request=request,
        name="inicio.html",
        context={
            "title": "Início",
            "active_page": "inicio",
            "no_sidebar": True,
            "operation_mode": settings.OPERATION_MODE,
            "timezone": settings.TIMEZONE,
            "drive_folder_id": settings.GOOGLE_DRIVE_FOLDER_ID,
            "metrics": {
                "videos_in_queue": videos_in_queue,
                "today_scheduled": today_scheduled,
                "connected_channels": connected_channels
            },
            "recent_projects": recent_projects,
            "upcoming_posts": upcoming_posts,
            "notifications": notifications
        }
    )
