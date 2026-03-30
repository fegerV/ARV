from datetime import datetime, timezone
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
        current_user=SimpleNamespace(),
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

        async def list_backups(self, db, limit, offset):
            self.calls.append((db, limit, offset))
            return records

    service = FakeBackupService()
    monkeypatch.setattr(backups, "BackupService", lambda: service)

    result = await backups.backup_history(
        limit=999,
        offset=-5,
        db=_FakeDb(),
        current_user=SimpleNamespace(),
    )

    assert service.calls[0][1:] == (100, 0)
    assert result == [
        {
            "id": 1,
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "status": "success",
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
        async def get_last_status(self, _db):
            return None

    monkeypatch.setattr(backups, "BackupService", FakeBackupService)

    result = await backups.backup_status(db=_FakeDb(), current_user=SimpleNamespace())

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
        async def get_last_status(self, _db):
            return record

    monkeypatch.setattr(backups, "BackupService", FakeBackupService)

    result = await backups.backup_status(db=_FakeDb(), current_user=SimpleNamespace())

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
        async def delete_backup(self, _db, _backup_id):
            return False

    monkeypatch.setattr(backups, "BackupService", FakeBackupService)

    with pytest.raises(HTTPException) as exc_info:
        await backups.delete_backup(404, db=_FakeDb(), current_user=SimpleNamespace())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Backup not found"


@pytest.mark.asyncio
async def test_delete_backup_returns_deleted_status(monkeypatch):
    from app.api.routes import backups

    class FakeBackupService:
        async def delete_backup(self, _db, backup_id):
            assert backup_id == 11
            return True

    monkeypatch.setattr(backups, "BackupService", FakeBackupService)

    result = await backups.delete_backup(11, db=_FakeDb(), current_user=SimpleNamespace())

    assert result == {"status": "deleted", "id": 11}


class _FakeDb:
    pass
