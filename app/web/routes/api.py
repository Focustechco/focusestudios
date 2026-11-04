import os
import uuid
import hashlib
import urllib.parse
from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
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
from app.models.media_asset import MediaAsset
from app.models.audit_event import AuditEvent

router = APIRouter(prefix="/api")


@router.post("/sync-now")
def api_sync_now(db: Session = Depends(get_db)):
    sync_svc = SyncService(db)
    sync_svc.sync_drive_folder(settings.GOOGLE_DRIVE_FOLDER_ID)
    inspect_svc = InspectionService(db)
    inspect_svc.inspect_all_pending()
    return RedirectResponse(url="/inicio", status_code=303)


@router.post("/upload-video")
async def api_upload_video(file: UploadFile = File(...), db: Session = Depends(get_db)):
    storage_dir = os.path.join("data", "storage", "media")
    os.makedirs(storage_dir, exist_ok=True)
    
    content = await file.read()
    sha256 = hashlib.sha256(content).hexdigest()
    
    local_path = os.path.join(storage_dir, file.filename)
    with open(local_path, "wb") as f:
        f.write(content)
        
    existing = db.query(MediaAsset).filter_by(sha256_hash=sha256).first()
    if not existing:
        asset = MediaAsset(
            drive_file_id=f"upload_{uuid.uuid4().hex[:12]}",
            name=file.filename,
            mime_type=file.content_type or "video/mp4",
            file_size_bytes=len(content),
            sha256_hash=sha256,
            local_storage_path=local_path,
            status="DISCOVERED"
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        inspect_svc = InspectionService(db)
        inspect_svc.inspect_asset(asset.id)
        
        event = AuditEvent(
            action="VIDEO_UPLOADED",
            entity_type="MediaAsset",
            entity_id=asset.id,
            user_or_system="operator",
            details=f"Vídeo {file.filename} enviado via upload direto no módulo Início."
        )
        db.add(event)
        db.commit()

    return RedirectResponse(url="/inicio", status_code=303)


@router.get("/media/{asset_id}/video")
def get_media_video(asset_id: str, db: Session = Depends(get_db)):
    asset = db.query(MediaAsset).filter_by(id=asset_id).first()
    if not asset or not asset.local_storage_path:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado.")
    
    abs_path = os.path.abspath(asset.local_storage_path)
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="Arquivo de vídeo não encontrado no disco local.")
        
    return FileResponse(
        path=abs_path,
        media_type=asset.mime_type or "video/mp4",
        filename=asset.name,
        headers={"Accept-Ranges": "bytes"}
    )


@router.get("/media/draft/{draft_id}/video")
def get_draft_video(draft_id: str, db: Session = Depends(get_db)):
    draft = db.query(PostDraft).filter_by(id=draft_id).first()
    if not draft or not draft.media_asset_id:
        raise HTTPException(status_code=404, detail="Rascunho ou mídia não encontrada.")
    return get_media_video(draft.media_asset_id, db)


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


@router.post("/publish-now")
def api_publish_now(
    post_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    from app.services.publisher_service import PublisherService
    pub_svc = PublisherService(db)

    if post_id:
        post = db.query(ScheduledPost).filter_by(id=post_id).first()
        if post:
            post.status = "UPLOADING"
            db.commit()
            res = pub_svc.execute_publish(post_id)
            err_param = ""
            if res.get("status") in ("FAILED", "UNKNOWN", "error", "blocked"):
                err_msg = res.get("message") or res.get("error") or "Falha no disparo do vídeo."
                err_param = f"&error={urllib.parse.quote(str(err_msg))}"
            return RedirectResponse(url=f"/calendar?status={res.get('status')}{err_param}", status_code=303)
        return RedirectResponse(url="/calendar", status_code=303)

    # Dispara os próximos posts agendados
    posts = db.query(ScheduledPost).filter(
        ScheduledPost.status.in_(["SCHEDULED", "PROCESSING", "NEEDS_REVIEW"])
    ).order_by(ScheduledPost.scheduled_time_utc.asc()).all()

    last_res = None
    published_count = 0
    for p in posts[:2]:
        p.status = "UPLOADING"
        db.commit()
        last_res = pub_svc.execute_publish(p.id)
        if last_res.get("status") == "PUBLISHED":
            published_count += 1
        elif last_res.get("status") in ("FAILED", "UNKNOWN", "error", "blocked"):
            p.status = "SCHEDULED"
            db.commit()
            err_msg = last_res.get("message") or last_res.get("error") or "Erro na publicação"
            if "spam_risk_too_many_pending_share" in str(err_msg):
                err_msg = "Limite de rascunhos pendentes no TikTok atingido (spam_risk_too_many_pending_share). Para postar direto no feed sem essa trava, reconecte a conta em Conexões para ativar o escopo Direct Post recém-adicionado (video.publish)."
            return RedirectResponse(url=f"/calendar?error={urllib.parse.quote(str(err_msg))}", status_code=303)

    return RedirectResponse(url=f"/calendar?published_count={published_count}", status_code=303)

