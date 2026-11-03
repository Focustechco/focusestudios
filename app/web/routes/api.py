from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.config import settings
from app.services.sync_service import SyncService
from app.services.inspection_service import InspectionService
from app.services.calendar_service import CalendarService
from app.services.approval_service import ApprovalService
from app.models.scheduled_post import ScheduledPost
from app.models.post_draft import PostDraft

router = APIRouter(prefix="/api")


@router.post("/sync-now")
def api_sync_now(db: Session = Depends(get_db)):
    sync_svc = SyncService(db)
    sync_svc.sync_drive_folder(settings.GOOGLE_DRIVE_FOLDER_ID)
    inspect_svc = InspectionService(db)
    inspect_svc.inspect_all_pending()
    return RedirectResponse(url="/", status_code=303)


@router.post("/inspect-all")
def api_inspect_all(db: Session = Depends(get_db)):
    inspect_svc = InspectionService(db)
    inspect_svc.inspect_all_pending()
    return RedirectResponse(url="/library", status_code=303)


@router.post("/schedule-batch")
def api_schedule_batch(db: Session = Depends(get_db)):
    cal_svc = CalendarService(db)
    cal_svc.schedule_approved_drafts(days_ahead=3)
    return RedirectResponse(url="/calendar", status_code=303)


@router.post("/drafts/{draft_id}/update-and-approve")
def api_update_and_approve(
    draft_id: str,
    title: str = Form(...),
    caption: str = Form(""),
    hashtags: str = Form(""),
    privacy_level: str = Form("SELF_ONLY"),
    disable_comment: Optional[bool] = Form(False),
    disable_duet: Optional[bool] = Form(False),
    disable_stitch: Optional[bool] = Form(False),
    is_aigc: Optional[bool] = Form(False),
    brand_content_toggle: Optional[bool] = Form(False),
    brand_organic_toggle: Optional[bool] = Form(False),
    action: str = Form("save_only"),
    db: Session = Depends(get_db)
):
    app_svc = ApprovalService(db)
    draft = app_svc.update_draft(
        draft_id=draft_id,
        title=title,
        caption=caption,
        hashtags=hashtags,
        privacy_level=privacy_level,
        disable_comment=bool(disable_comment),
        disable_duet=bool(disable_duet),
        disable_stitch=bool(disable_stitch),
        is_aigc=bool(is_aigc),
        brand_content_toggle=bool(brand_content_toggle),
        brand_organic_toggle=bool(brand_organic_toggle)
    )

    if action == "approve":
        app_svc.approve_draft(draft_id=draft.id, approved_by="operador")

    return RedirectResponse(url=f"/review?draft_id={draft_id}", status_code=303)


@router.post("/posts/{post_id}/cancel")
def api_cancel_post(post_id: str, db: Session = Depends(get_db)):
    post = db.query(ScheduledPost).filter_by(id=post_id).first()
    if post and post.status == "SCHEDULED":
        post.status = "CANCELLED"
        if post.post_draft:
            post.post_draft.status = "READY"
        db.commit()
    return RedirectResponse(url="/calendar", status_code=303)


@router.post("/connections/toggle-mode")
def api_toggle_mode():
    modes = ["DEMO", "MANUAL_STUDIO", "DIRECT_POST"]
    cur_idx = modes.index(settings.OPERATION_MODE) if settings.OPERATION_MODE in modes else 0
    settings.OPERATION_MODE = modes[(cur_idx + 1) % len(modes)]
    return RedirectResponse(url="/connections", status_code=303)


@router.post("/settings/update")
def api_update_settings(
    operation_mode: str = Form(...),
    daily_target: int = Form(10),
    tolerance_minutes: int = Form(15),
    ai_caption_enabled: Optional[bool] = Form(False)
):
    settings.OPERATION_MODE = operation_mode
    settings.DAILY_POST_TARGET = daily_target
    settings.OVERDUE_TOLERANCE_MINUTES = tolerance_minutes
    settings.AI_CAPTION_ENABLED = bool(ai_caption_enabled)
    return RedirectResponse(url="/settings?saved=true", status_code=303)
