from typing import Optional
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.media_asset import MediaAsset
from app.core.timezone import to_fortaleza, format_fortaleza
from app.web.templates_env import templates

router = APIRouter()


def format_duration(seconds: float | None) -> str:
    if not seconds or seconds <= 0:
        return "00:00"
    total_sec = int(round(seconds))
    mins = total_sec // 60
    secs = total_sec % 60
    return f"{mins:02d}:{secs:02d}"


@router.get("/library", response_class=HTMLResponse)
def get_library(
    request: Request,
    view: str = Query("cards"),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(MediaAsset).order_by(MediaAsset.created_at.desc())
    if search:
        query = query.filter(MediaAsset.name.ilike(f"%{search}%"))
    if status and status != "ALL":
        query = query.filter(MediaAsset.status == status)

    assets_raw = query.all()

    assets = []
    for a in assets_raw:
        draft = a.post_drafts[0] if a.post_drafts else None
        size_mb = round((a.file_size_bytes or 0) / (1024 * 1024), 2)
        dur_str = format_duration(a.duration_seconds)
        resolution_str = f"{a.width}x{a.height}" if (a.width and a.height) else "1080x1920"
        created_str = format_fortaleza(a.created_at) if a.created_at else ""

        assets.append({
            "id": a.id,
            "name": a.name,
            "title": draft.title if (draft and draft.title) else a.name,
            "draft_id": draft.id if draft else None,
            "draft_status": draft.status if draft else None,
            "size_mb": size_mb,
            "duration": dur_str,
            "duration_seconds": a.duration_seconds or 0,
            "width": a.width or 1080,
            "height": a.height or 1920,
            "resolution": resolution_str,
            "aspect_ratio": a.aspect_ratio or "9:16",
            "video_codec": a.video_codec or "h264",
            "audio_codec": a.audio_codec or "aac",
            "status": a.status,
            "sha256_hash": a.sha256_hash,
            "created_at": created_str,
        })

    return templates.TemplateResponse(
        request=request,
        name="library.html",
        context={
            "title": "Biblioteca de Mídia",
            "active_page": "library",
            "operation_mode": settings.OPERATION_MODE,
            "timezone": settings.TIMEZONE,
            "assets": assets,
            "view_mode": view,
            "search_term": search or "",
            "selected_status": status or "ALL"
        }
    )

