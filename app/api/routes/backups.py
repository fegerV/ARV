"""API endpoints for database backup management.

All endpoints require a super admin, mirroring the pages that call them
(``/backups`` and the Backups tab of ``/settings``, both super-admin only).
Backups are a platform-level resource: every artifact is written to a single
company's Yandex Disk, so ``backup_history.company_id`` records *whose storage
holds the file*, not which tenant owns the data. Scoping these endpoints by that
column therefore handed the storage company's own users the ability to trigger,
enumerate and delete the platform's backups — the HTML pages never exposed that,
and neither does this module any more.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from app.api.deps_authz import require_super_admin
from app.core.database import get_db
from app.models.user import User
from app.services.backup_service import BackupService
from app.services.restore_service import (
    ArtifactUnavailable,
    DecryptionUnavailable,
    RestoreService,
)
from app.services.settings_service import SettingsService

router = APIRouter()


def _safe_filename(name: str, fallback: str) -> str:
    """Reduce *name* to characters that are safe in a header and a path.

    The name originates from a stored artifact path, so it is not attacker
    controlled today — but it is also not something to trust implicitly in a
    ``Content-Disposition`` header, where a stray quote or newline is enough to
    corrupt the response.
    """
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(name or ""))
    return cleaned or fallback


@router.post("/run")
async def run_backup_now(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
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
    current_user: User = Depends(require_super_admin),
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
            "backup_type": getattr(r, "backup_type", None) or "db",
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
    current_user: User = Depends(require_super_admin),
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
    current_user: User = Depends(require_super_admin),
) -> dict:
    """Delete a backup record and its file on Yandex Disk."""
    service = BackupService()
    deleted = await service.delete_backup(db, backup_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Backup not found")
    return {"status": "deleted", "id": backup_id}


@router.get("/{backup_id}/download")
async def download_backup(
    backup_id: int,
    decrypt: bool = False,
    current_user: User = Depends(require_super_admin),
) -> FileResponse:
    """Download a stored backup artifact as a file.

    Super-admin only, and deliberately not widened to company scope: a database
    artifact holds every tenant's data, and the secrets artifact holds
    ``SECRET_KEY``. The page that offers the button is already super-admin, so
    this matches the surface it lives on instead of exposing more.

    The artifact is returned exactly as stored — age-encrypted for db and
    secrets backups. ``?decrypt=true`` opens it only when the age identity is
    mounted on this host; without the key the answer is 400 rather than an
    encrypted file under a name implying it was decrypted.

    Media backups are ``restic`` snapshots and have no single file, so they
    answer 409 with the alternative.
    """
    workdir = tempfile.mkdtemp(prefix="arv-download-")
    try:
        info = await RestoreService().fetch_artifact(backup_id, workdir, decrypt=decrypt)
    except ArtifactUnavailable as exc:
        shutil.rmtree(workdir, ignore_errors=True)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DecryptionUnavailable as exc:
        shutil.rmtree(workdir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (RuntimeError, ValueError) as exc:
        shutil.rmtree(workdir, ignore_errors=True)
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return FileResponse(
        info["path"],
        filename=_safe_filename(info["filename"], f"backup_{backup_id}"),
        media_type="application/octet-stream",
        # The artifact is materialised into a temp directory purely to be sent;
        # cleaning up after the response is the only place that can know the
        # transfer finished.
        background=BackgroundTask(shutil.rmtree, workdir, ignore_errors=True),
    )
