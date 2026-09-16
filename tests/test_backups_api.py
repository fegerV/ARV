from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException


@pytest.mark.asyncio
async def test_run_backup_now_requires_configured_company(monkeypatch):
    from app.api.routes import backups

    class FakeSettingsService:
        def __init__(self, _db):
            pass

        async def get_all_settings(self):
            return SimpleNamespace(
                backup=SimpleNamespace(
                    backup_company_id=None,
                    backup_yd_folder="backups",
                )
            )

    monkeypatch.setattr(backups, "SettingsService", FakeSettingsService)

    with pytest.raises(HTTPException) as exc_info:
        await backups.run_backup_now(
            background_tasks=BackgroundTasks(),
            db=_FakeDb(),
            current_user=SimpleNamespace(),
        )

    assert exc_info.value.status_code == 400
    assert "Backup company not configured" in exc_info.value.detail


@pytest.mark.asyncio
async def test_run_backup_now_queues_background_task(monkeypatch):
    from app.api.routes import backups

    class FakeSettingsService:
        def __init__(self, _db):
            pass

        async def get_all_settings(self):
            return SimpleNamespace(
                backup=SimpleNamespace(
                    backup_company_id=17,
                    backup_yd_folder="yd/backups",
                )
            )

    calls = []

    class FakeBackupService:
        async def run_backup(self, company_id, yd_folder, trigger):
            calls.append((company_id, yd_folder, trigger))

    monkeypatch.setattr(backups, "SettingsService", FakeSettingsService)
    monkeypatch.setattr(backups, "BackupService", FakeBackupService)

    tasks = BackgroundTasks()
    result = await backups.run_backup_now(
        background_tasks=tasks,
        db=_FakeDb(),
        current_user=SimpleNamespace(is_super_admin=True),
    )

    assert result == {"status": "started", "message": "Backup task queued"}
    assert len(tasks.tasks) == 1
    task = tasks.tasks[0]
    assert task.args == ()
    assert task.kwargs == {"company_id": 17, "yd_folder": "yd/backups", "trigger": "manual"}
    assert calls == []


@pytest.mark.asyncio
async def test_backup_history_clamps_limit_and_normalizes_offset(monkeypatch):
    from app.api.routes import backups

    started = datetime.now(timezone.utc).replace(tzinfo=None)
    finished = started.replace(hour=(started.hour + 1) % 24)
    records = [
        SimpleNamespace(
            id=1,
            started_at=started,
            finished_at=finished,
            status="success",
            backup_type="db",
            size_bytes=2048,
            yd_path="backups/file.sql.gz",
            company_id=7,
            error_message=None,
            trigger="manual",
        )
    ]

    class FakeBackupService:
        def __init__(self):
            self.calls = []

        async def list_backups(self, db, limit, offset, company_ids=None):
            self.calls.append((db, limit, offset))
            return records

    service = FakeBackupService()
    monkeypatch.setattr(backups, "BackupService", lambda: service)

    result = await backups.backup_history(
        limit=999,
        offset=-5,
        db=_FakeDb(),
        current_user=SimpleNamespace(is_super_admin=True),
    )

    assert service.calls[0][1:] == (100, 0)
    assert result == [
        {
            "id": 1,
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "status": "success",
            # Exposed so a client can tell which rows are downloadable at all.
            "backup_type": "db",
            "size_bytes": 2048,
            "yd_path": "backups/file.sql.gz",
            "company_id": 7,
            "error_message": None,
            "trigger": "manual",
        }
    ]


@pytest.mark.asyncio
async def test_backup_status_returns_no_backups_when_empty(monkeypatch):
    from app.api.routes import backups

    class FakeBackupService:
        async def get_last_status(self, _db, company_ids=None):
            return None

    monkeypatch.setattr(backups, "BackupService", FakeBackupService)

    result = await backups.backup_status(db=_FakeDb(), current_user=SimpleNamespace(is_super_admin=True))

    assert result == {"status": "no_backups"}


@pytest.mark.asyncio
async def test_backup_status_serializes_last_record(monkeypatch):
    from app.api.routes import backups

    started = datetime.now(timezone.utc).replace(tzinfo=None)
    finished = started.replace(hour=(started.hour + 1) % 24)
    record = SimpleNamespace(
        id=9,
        started_at=started,
        finished_at=finished,
        status="failed",
        size_bytes=None,
        yd_path=None,
        error_message="boom",
        trigger="scheduled",
    )

    class FakeBackupService:
        async def get_last_status(self, _db, company_ids=None):
            return record

    monkeypatch.setattr(backups, "BackupService", FakeBackupService)

    result = await backups.backup_status(db=_FakeDb(), current_user=SimpleNamespace(is_super_admin=True))

    assert result == {
        "id": 9,
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "status": "failed",
        "size_bytes": None,
        "yd_path": None,
        "error_message": "boom",
        "trigger": "scheduled",
    }


@pytest.mark.asyncio
async def test_delete_backup_raises_for_missing_record(monkeypatch):
    from app.api.routes import backups

    class FakeBackupService:
        async def delete_backup(self, _db, _backup_id, company_ids=None):
            return False

    monkeypatch.setattr(backups, "BackupService", FakeBackupService)

    with pytest.raises(HTTPException) as exc_info:
        await backups.delete_backup(404, db=_FakeDb(), current_user=SimpleNamespace(is_super_admin=True))

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Backup not found"


@pytest.mark.asyncio
async def test_delete_backup_returns_deleted_status(monkeypatch):
    from app.api.routes import backups

    class FakeBackupService:
        async def delete_backup(self, _db, backup_id, company_ids=None):
            assert backup_id == 11
            return True

    monkeypatch.setattr(backups, "BackupService", FakeBackupService)

    result = await backups.delete_backup(11, db=_FakeDb(), current_user=SimpleNamespace(is_super_admin=True))

    assert result == {"status": "deleted", "id": 11}


class _FakeDb:
    pass


# ----------------------------------------------------------------------
# download
# ----------------------------------------------------------------------


def _stub_fetch(monkeypatch, backups, payload=b"cipher", name="backup_20260915.sql.gz.age"):
    """Point the endpoint at a fake fetch_artifact that writes *payload*."""
    seen: dict = {}

    async def _fake_fetch(self, backup_id, workdir, *, decrypt=False):
        seen["backup_id"] = backup_id
        seen["decrypt"] = decrypt
        path = Path(workdir) / name
        path.write_bytes(payload)
        return {
            "path": str(path),
            "filename": name,
            "encrypted": True,
            "plaintext": not decrypt,
            "size_bytes": len(payload),
            "backup_type": "db",
        }

    monkeypatch.setattr(backups.RestoreService, "fetch_artifact", _fake_fetch)
    return seen


@pytest.mark.asyncio
async def test_download_backup_streams_the_artifact_and_cleans_up(monkeypatch):
    from app.api.routes import backups

    _stub_fetch(monkeypatch, backups)

    response = await backups.download_backup(
        42, decrypt=False, current_user=SimpleNamespace(is_super_admin=True)
    )

    assert response.filename == "backup_20260915.sql.gz.age"
    assert Path(response.path).read_bytes() == b"cipher"

    # The artifact is materialised into a temp dir only to be sent. If the
    # background cleanup is missing, every download leaks a copy of the
    # database — or of SECRET_KEY — into /tmp.
    assert response.background is not None
    await response.background()
    assert not Path(response.path).exists()


@pytest.mark.asyncio
async def test_download_backup_passes_decrypt_through(monkeypatch):
    from app.api.routes import backups

    seen = _stub_fetch(monkeypatch, backups)

    await backups.download_backup(
        42, decrypt=True, current_user=SimpleNamespace(is_super_admin=True)
    )

    assert seen == {"backup_id": 42, "decrypt": True}


@pytest.mark.asyncio
async def test_download_backup_maps_media_to_409(monkeypatch):
    from app.api.routes import backups
    from app.services.restore_service import ArtifactUnavailable

    async def _boom(self, backup_id, workdir, *, decrypt=False):
        raise ArtifactUnavailable("Media backups are restic snapshots, not a single file.")

    monkeypatch.setattr(backups.RestoreService, "fetch_artifact", _boom)

    with pytest.raises(HTTPException) as exc_info:
        await backups.download_backup(
            42, decrypt=False, current_user=SimpleNamespace(is_super_admin=True)
        )

    # 409, not 500: the request is understood, it just does not apply.
    assert exc_info.value.status_code == 409
    assert "restic" in exc_info.value.detail


@pytest.mark.asyncio
async def test_download_backup_maps_a_missing_identity_to_400(monkeypatch):
    from app.api.routes import backups
    from app.services.restore_service import DecryptionUnavailable

    async def _boom(self, backup_id, workdir, *, decrypt=False):
        raise DecryptionUnavailable("no identity on this host")

    monkeypatch.setattr(backups.RestoreService, "fetch_artifact", _boom)

    with pytest.raises(HTTPException) as exc_info:
        await backups.download_backup(
            42, decrypt=True, current_user=SimpleNamespace(is_super_admin=True)
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_download_backup_maps_a_missing_record_to_404(monkeypatch):
    from app.api.routes import backups

    async def _boom(self, backup_id, workdir, *, decrypt=False):
        raise RuntimeError(f"Backup {backup_id} not found")

    monkeypatch.setattr(backups.RestoreService, "fetch_artifact", _boom)

    with pytest.raises(HTTPException) as exc_info:
        await backups.download_backup(
            999, decrypt=False, current_user=SimpleNamespace(is_super_admin=True)
        )

    assert exc_info.value.status_code == 404


def test_safe_filename_strips_anything_unsafe():
    from app.api.routes.backups import _safe_filename

    # A filename reaches the Content-Disposition header, where a quote or a
    # newline is enough to corrupt the response.
    assert _safe_filename('bad"name\r\n.sql.gz', "fallback") == "bad_name__.sql.gz"
    assert _safe_filename("", "fallback") == "fallback"
    assert _safe_filename("backup_20260915.sql.gz.age", "fallback") == (
        "backup_20260915.sql.gz.age"
    )
