"""Tests for ``app/services/media_backup_service.py`` (restic orchestration).

restic itself is exercised by the operational drill; these tests pin the
orchestration contract: what gets invoked, how the snapshot is recorded, and
that a disabled deployment produces no noise.
"""

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.utils.command import CommandError


def _media_settings(**overrides) -> SimpleNamespace:
    base = {
        "BACKUP_MEDIA_ENABLED": True,
        "BACKUP_RESTIC_BINARY": "restic",
        "BACKUP_RESTIC_REPOSITORY": "s3:example.com/arv-backups/restic-media",
        "BACKUP_RESTIC_PASSWORD_FILE": "/etc/arv/restic.pass",
        "BACKUP_KEEP_DAILY": 7,
        "BACKUP_KEEP_WEEKLY": 4,
        "BACKUP_KEEP_MONTHLY": 12,
        "BACKUP_KEEP_YEARLY": 3,
        "backup_media_paths": ["/opt/arv/storage"],
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_available_is_false_when_disabled(monkeypatch):
    from app.services import media_backup_service

    monkeypatch.setattr(
        media_backup_service, "settings", _media_settings(BACKUP_MEDIA_ENABLED=False)
    )

    assert media_backup_service.MediaBackupService.available() is False


def test_available_is_false_without_repository(monkeypatch):
    from app.services import media_backup_service

    monkeypatch.setattr(
        media_backup_service, "settings", _media_settings(BACKUP_RESTIC_REPOSITORY="")
    )

    assert media_backup_service.MediaBackupService.available() is False


def test_available_is_false_when_restic_binary_is_missing(monkeypatch):
    from app.services import media_backup_service

    monkeypatch.setattr(media_backup_service, "settings", _media_settings())
    monkeypatch.setattr(media_backup_service, "binary_available", lambda _b: False)

    assert media_backup_service.MediaBackupService.available() is False


def test_available_is_true_when_fully_configured(monkeypatch):
    from app.services import media_backup_service

    monkeypatch.setattr(media_backup_service, "settings", _media_settings())
    monkeypatch.setattr(media_backup_service, "binary_available", lambda _b: True)

    assert media_backup_service.MediaBackupService.available() is True


def test_restic_env_uses_a_password_file_never_a_literal(monkeypatch):
    from app.services import media_backup_service

    monkeypatch.setattr(media_backup_service, "settings", _media_settings())

    env = media_backup_service.MediaBackupService._restic_env()

    assert env["RESTIC_REPOSITORY"] == "s3:example.com/arv-backups/restic-media"
    assert env["RESTIC_PASSWORD_FILE"] == "/etc/arv/restic.pass"
    assert "RESTIC_PASSWORD" not in env


def test_gfs_args_match_the_documented_ladder(monkeypatch):
    from app.services import media_backup_service

    monkeypatch.setattr(media_backup_service, "settings", _media_settings())

    assert media_backup_service.MediaBackupService._gfs_args() == [
        "--keep-daily", "7",
        "--keep-weekly", "4",
        "--keep-monthly", "12",
        "--keep-yearly", "3",
    ]


@pytest.mark.asyncio
async def test_run_backup_returns_none_when_not_configured(monkeypatch):
    from app.services import media_backup_service

    monkeypatch.setattr(
        media_backup_service, "settings", _media_settings(BACKUP_MEDIA_ENABLED=False)
    )

    result = await media_backup_service.MediaBackupService().run_backup()

    assert result is None


@pytest.mark.asyncio
async def test_snapshot_parses_the_summary_message(monkeypatch):
    from app.services import media_backup_service

    stream = "\n".join(
        [
            json.dumps({"message_type": "status", "percent_done": 0.5}),
            json.dumps(
                {
                    "message_type": "summary",
                    "snapshot_id": "a1b2c3d4",
                    "total_bytes_processed": 123456,
                }
            ),
        ]
    )

    captured: dict = {}

    async def _fake_run_command(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs.get("env")
        return stream

    monkeypatch.setattr(media_backup_service, "settings", _media_settings())
    monkeypatch.setattr(media_backup_service, "run_command", _fake_run_command)

    snapshot_id, size = await media_backup_service.MediaBackupService()._snapshot(
        ["/opt/arv/storage"]
    )

    assert snapshot_id == "a1b2c3d4"
    assert size == 123456
    assert captured["cmd"][1] == "backup"
    assert "/opt/arv/storage" in captured["cmd"]
    assert "--json" in captured["cmd"]
    assert captured["env"]["RESTIC_REPOSITORY"].startswith("s3:")


@pytest.mark.asyncio
async def test_run_backup_records_snapshot_and_applies_rotation(monkeypatch):
    from app.services import media_backup_service

    session = _FakeSession()

    calls: list[str] = []
    heartbeats: list[str] = []

    async def _fake_run_command(cmd, **kwargs):
        calls.append(cmd[1])
        if cmd[1] == "backup":
            return json.dumps(
                {
                    "message_type": "summary",
                    "snapshot_id": "snap-42",
                    "total_bytes_processed": 999,
                }
            )
        return ""

    async def _fake_heartbeat(status="success", detail=""):
        heartbeats.append(status)
        return True

    monkeypatch.setattr(media_backup_service, "settings", _media_settings())
    monkeypatch.setattr(media_backup_service, "binary_available", lambda _b: True)
    monkeypatch.setattr(media_backup_service, "run_command", _fake_run_command)
    monkeypatch.setattr(media_backup_service, "send_heartbeat", _fake_heartbeat)
    monkeypatch.setattr(
        media_backup_service, "AsyncSessionLocal", _sticky_factory(session)
    )

    result = await media_backup_service.MediaBackupService().run_backup(
        trigger="scheduled", session=session
    )

    assert result.status == "success"
    assert result.snapshot_id == "snap-42"
    assert result.size_bytes == 999
    assert result.backup_type == "media"
    assert result.encrypted is True  # restic always encrypts
    assert result.duration_seconds is not None
    assert calls == ["backup", "forget"]
    assert heartbeats == ["success"]


@pytest.mark.asyncio
async def test_run_backup_marks_failure_and_pings_heartbeat(monkeypatch):
    from app.services import media_backup_service

    session = _FakeSession()

    heartbeats: list[str] = []

    async def _boom(cmd, **kwargs):
        raise CommandError("restic backup exited with code 1: repository locked")

    async def _fake_heartbeat(status="success", detail=""):
        heartbeats.append(status)
        return True

    monkeypatch.setattr(media_backup_service, "settings", _media_settings())
    monkeypatch.setattr(media_backup_service, "binary_available", lambda _b: True)
    monkeypatch.setattr(media_backup_service, "run_command", _boom)
    monkeypatch.setattr(media_backup_service, "send_heartbeat", _fake_heartbeat)
    monkeypatch.setattr(
        media_backup_service, "AsyncSessionLocal", _sticky_factory(session)
    )

    result = await media_backup_service.MediaBackupService().run_backup(
        trigger="scheduled", session=session
    )

    assert result.status == "failed"
    assert "repository locked" in result.error_message
    assert heartbeats == ["fail"]


@pytest.mark.asyncio
async def test_check_integrity_reports_failure_without_raising(monkeypatch):
    from app.services import media_backup_service

    async def _boom(cmd, **kwargs):
        raise CommandError("restic check exited with code 1: pack corrupted")

    monkeypatch.setattr(media_backup_service, "settings", _media_settings())
    monkeypatch.setattr(media_backup_service, "binary_available", lambda _b: True)
    monkeypatch.setattr(media_backup_service, "run_command", _boom)

    service = media_backup_service.MediaBackupService()
    monkeypatch.setattr(service, "_mark_verified", _async_noop())

    assert await service.check_integrity() is False


@pytest.mark.asyncio
async def test_check_integrity_uses_a_read_data_subset(monkeypatch):
    from app.services import media_backup_service

    captured: dict = {}

    async def _fake_run_command(cmd, **kwargs):
        captured["cmd"] = cmd
        return ""

    monkeypatch.setattr(media_backup_service, "settings", _media_settings())
    monkeypatch.setattr(media_backup_service, "binary_available", lambda _b: True)
    monkeypatch.setattr(media_backup_service, "run_command", _fake_run_command)

    service = media_backup_service.MediaBackupService()
    monkeypatch.setattr(service, "_mark_verified", _async_noop())

    assert await service.check_integrity("5%") is True
    assert "--read-data-subset=5%" in captured["cmd"]


@pytest.mark.asyncio
async def test_mark_verified_stamps_the_newest_media_record(monkeypatch):
    from app.services import media_backup_service

    record = SimpleNamespace(verified_at=None, verification_status=None)
    session = _FakeSession(execute_results=[_ScalarOneOrNone(record)])

    monkeypatch.setattr(
        media_backup_service, "AsyncSessionLocal", _sticky_factory(session)
    )

    await media_backup_service.MediaBackupService()._mark_verified(True)

    assert record.verification_status == "ok"
    assert record.verified_at is not None
    assert session.commit_calls == 1


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


class _ScalarOneOrNone:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeSession:
    def __init__(self, get_map=None, execute_results=None):
        self.get_map = get_map or {}
        self.execute_results = list(execute_results or [])
        self.commit_calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, model, pk):
        return self.get_map.get((model, pk))

    async def execute(self, _stmt):
        return self.execute_results.pop(0)

    async def commit(self):
        self.commit_calls += 1

    def add(self, obj):
        # Mirror the ORM: a flushed object becomes retrievable by primary key,
        # which is what the service relies on when it re-reads its own row.
        if getattr(obj, "id", None) is None:
            obj.id = 501
        self.get_map[(type(obj), obj.id)] = obj

    async def refresh(self, obj):
        return None


def _sticky_factory(session):
    """Return the same session for every ``AsyncSessionLocal()`` call."""
    return lambda: session


def _async_noop():
    async def _inner(*args, **kwargs):
        return None

    return _inner
