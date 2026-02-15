"""API endpoints for database backup management.

All endpoints require an authenticated admin session.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.services.backup_service import BackupService
from app.services.settings_service import SettingsService

router = APIRouter()


@router.post("/run")
async def run_backup_now(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Trigger an immediate database backup.

    The actual backup runs as a background task so the response is
    returned quickly.
    """
    svc = SettingsService(db)
    all_settings = await svc.get_all_settings()
    bkp = all_settings.backup

    if not bkp.backup_company_id:
        raise HTTPException(
            status_code=400,
            detail="Backup company not configured. Go to Settings → Backups.",
        )

    backup_service = BackupService()
    background_tasks.add_task(
        backup_service.run_backup,
        company_id=bkp.backup_company_id,
        yd_folder=bkp.backup_yd_folder,
        trigger="manual",
    )

    return {"status": "started", "message": "Backup task queued"}


@router.get("/history")
async def backup_history(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[dict]:
    """Return recent backup records."""
    service = BackupService()
    records = await service.list_backups(db, limit=min(limit, 100), offset=max(offset, 0))
    return [
        {
            "id": r.id,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "status": r.status,
            "size_bytes": r.size_bytes,
            "yd_path": r.yd_path,
            "company_id": r.company_id,
            "error_message": r.error_message,
            "trigger": r.trigger,
        }
        for r in records
    ]


@router.get("/status")
async def backup_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Return the status of the most recent backup."""
    service = BackupService()
    last = await service.get_last_status(db)
    if not last:
        return {"status": "no_backups"}
    return {
        "id": last.id,
        "started_at": last.started_at.isoformat() if last.started_at else None,
        "finished_at": last.finished_at.isoformat() if last.finished_at else None,
        "status": last.status,
        "size_bytes": last.size_bytes,
        "yd_path": last.yd_path,
        "error_message": last.error_message,
        "trigger": last.trigger,
    }


@router.delete("/{backup_id}")
async def delete_backup(
    backup_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Delete a backup record and its file on Yandex Disk."""
    service = BackupService()
    deleted = await service.delete_backup(db, backup_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Backup not found")
    return {"status": "deleted", "id": backup_id}
