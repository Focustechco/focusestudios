from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.services.studio_exporter import StudioExporter

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


@router.get("/export/studio", response_class=HTMLResponse)
def get_export_studio(request: Request, db: Session = Depends(get_db)):
    exporter = StudioExporter(db)
    items = exporter.get_manual_studio_items()

    return templates.TemplateResponse(
        request=request,
        name="export_studio.html",
        context={
            "title": "TikTok Studio Manual",
            "active_page": "export_studio",
            "operation_mode": settings.OPERATION_MODE,
            "timezone": settings.TIMEZONE,
            "items": items
        }
    )


@router.get("/api/export/studio/manifest.csv")
def download_manifest_csv(db: Session = Depends(get_db)):
    exporter = StudioExporter(db)
    csv_content = exporter.generate_manifest_csv()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=tiktok_studio_manifest_focustech.csv"
        }
    )
