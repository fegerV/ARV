"""HTML route for the Backups page - history, run, status."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_current_active_user
from app.core.database import get_db
from app.html.filters import datetime_format
from app.models.user import User
from app.services.backup_service import BackupService
from app.services.settings_service import SettingsService

router = APIRouter()
templates = Jinja2Templates(directory="templates")
templates.env.filters["datetime_format"] = datetime_format


@router.get("/backups", response_class=HTMLResponse)
async def backups_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Page for backup management."""
    svc = BackupService()
    settings_svc = SettingsService(db)
    all_settings = await settings_svc.get_all_settings()

    records = await svc.list_backups(db, limit=50, offset=0)
    last_status = await svc.get_last_status(db)

    backup_configured = bool(all_settings.backup.backup_company_id)

    return templates.TemplateResponse(
        "admin/backups.html",
        {
            "request": request,
            "current_user": current_user,
            "records": records,
            "last_status": last_status,
            "backup_configured": backup_configured,
        },
    )
