"""Tests for the hardened backup pipeline in ``app/services/backup_service.py``.

These cover the P0 gaps identified in ``docs/BACKUP_AND_RECOVERY.md`` §13.2:
missing encryption, a single off-site copy, non-GFS rotation and the absence of
any alerting when a run fails.
"""

import hashlib
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest


# ----------------------------------------------------------------------
# Encryption + dual off-site
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_backup_encrypts_and_ships_to_both_targets(monkeypatch):
    from app.services import backup_service

    temp_dir = Path(tempfile.mkdtemp(prefix="backup-hardening-"))
    dump_path = temp_dir / "backup.dump"
    dump_path.write_bytes(b"custom-archive-payload" * 100)

    record = backup_service.BackupHistory(
        started_at=backup_service._utcnow_naive(),
        status="running",
        company_id=5,
        trigger="manual",
    )
    record.id = 901
    session = _FakeSession(get_map={(backup_service.BackupHistory, 901): record})

    class FakeProvider:
        def __init__(self):
            self.saved = []

        async def save_file(self, source_path, destination_path):
            self.saved.append((source_path, destination_path))
            return f"yadisk://{destination_path}"

    provider = FakeProvider()
    secondary: list[tuple[str, str, str]] = []
    heartbeats: list[str] = []

    async def _fake_encrypt(self, src, dst):
        shutil.copyfile(src, dst)

    async def _fake_secondary(self, src, remote_path):
        # Capture the digest while the artifact still exists on disk so the
        # assertion proves the recorded checksum matches the real bytes.
        digest = hashlib.sha256(Path(src).read_bytes()).hexdigest()
        secondary.append((src, remote_path, digest))
        return True

    async def _fake_heartbeat(status="success", detail=""):
        heartbeats.append(status)
        return True

    monkeypatch.setattr(
        backup_service,
        "settings",
        SimpleNamespace(encryption_enabled=True, secondary_target_enabled=True),
    )
    monkeypatch.setattr(backup_service, "AsyncSessionLocal", _SessionFactory([session]))
    monkeypatch.setattr(
        backup_service.BackupService, "_run_pg_dump", _async_return(str(dump_path))
    )
    monkeypatch.setattr(
        backup_service.BackupService,
        "_get_yd_provider",
        staticmethod(_async_return(provider)),
    )
    monkeypatch.setattr(backup_service.BackupService, "_encrypt_file", _fake_encrypt)
    monkeypatch.setattr(
        backup_service.BackupService, "_copy_to_secondary", _fake_secondary
    )
    monkeypatch.setattr(
        backup_service.BackupService, "_rotate_backups", _async_return(None)
    )
    monkeypatch.setattr(backup_service, "send_heartbeat", _fake_heartbeat)
    monkeypatch.setattr(backup_service.asyncio, "to_thread", _fake_to_thread)

    try:
        result = await backup_service.BackupService().run_backup(
            session=session, company_id=5, yd_folder="daily", trigger="manual"
        )

        assert result.status == "success"
        # Encrypted artifact is what actually leaves the host: the local
        # staging file carries the .age suffix and so does the remote object.
        assert provider.saved[0][0].endswith(".gz.age")
        assert provider.saved[0][1].endswith(".sql.gz.age")
        assert result.yd_path.startswith("daily/backup_")
        assert result.yd_path.endswith(".sql.gz.age")
        assert result.encrypted is True
        # 3-2-1: two independent off-site copies, same object.
        assert result.target == "primary+secondary"
        assert result.secondary_path == result.yd_path
        assert secondary[0][1] == result.yd_path
        # The recorded checksum must describe the artifact that was shipped.
        assert result.checksum == secondary[0][2]
        assert len(result.checksum) == 64
        assert heartbeats == ["success"]
    finally:
        for name in ("backup.dump", "backup.dump.gz", "backup.dump.gz.age"):
            leftover = temp_dir / name
            if leftover.exists():
                leftover.unlink()
        temp_dir.rmdir()


@pytest.mark.asyncio
async def test_run_backup_without_encryption_keeps_plain_gz_artifact(monkeypatch):
    from app.services import backup_service

    temp_dir = Path(tempfile.mkdtemp(prefix="backup-plain-"))
    dump_path = temp_dir / "backup.dump"
    dump_path.write_bytes(b"payload" * 50)

    record = backup_service.BackupHistory(
        started_at=backup_service._utcnow_naive(),
        status="running",
        company_id=5,
        trigger="manual",
    )
    record.id = 901
    session = _FakeSession(get_map={(backup_service.BackupHistory, 901): record})

    class FakeProvider:
        def __init__(self):
            self.saved = []

        async def save_file(self, source_path, destination_path):
            self.saved.append((source_path, destination_path))

    provider = FakeProvider()

    async def _must_not_be_called(self, src, dst):  # pragma: no cover
        raise AssertionError("age must not run when no recipient is configured")

    monkeypatch.setattr(
        backup_service,
        "settings",
        SimpleNamespace(encryption_enabled=False, secondary_target_enabled=False),
    )
    monkeypatch.setattr(backup_service, "AsyncSessionLocal", _SessionFactory([session]))
    monkeypatch.setattr(
        backup_service.BackupService, "_run_pg_dump", _async_return(str(dump_path))
    )
    monkeypatch.setattr(
        backup_service.BackupService,
        "_get_yd_provider",
        staticmethod(_async_return(provider)),
    )
    monkeypatch.setattr(
        backup_service.BackupService, "_encrypt_file", _must_not_be_called
    )
    monkeypatch.setattr(
        backup_service.BackupService, "_rotate_backups", _async_return(None)
    )
    monkeypatch.setattr(backup_service, "send_heartbeat", _async_return(True))
    monkeypatch.setattr(backup_service.asyncio, "to_thread", _fake_to_thread)

    try:
        result = await backup_service.BackupService().run_backup(
            session=session, company_id=5, yd_folder="daily", trigger="manual"
        )

        assert result.status == "success"
        assert result.encrypted is False
        assert provider.saved[0][0].endswith(".gz")
        assert provider.saved[0][1].endswith(".sql.gz")
        assert result.target == "primary"
        assert result.secondary_path is None
    finally:
        for name in ("backup.dump", "backup.dump.gz"):
            leftover = temp_dir / name
            if leftover.exists():
                leftover.unlink()
        temp_dir.rmdir()


@pytest.mark.asyncio
async def test_secondary_copy_failure_does_not_fail_the_backup(monkeypatch):
    """A failed second copy degrades redundancy, not the backup itself."""
    from app.services import backup_service

    temp_dir = Path(tempfile.mkdtemp(prefix="backup-secondary-"))
    dump_path = temp_dir / "backup.dump"
    dump_path.write_bytes(b"payload" * 50)

    record = backup_service.BackupHistory(
        started_at=backup_service._utcnow_naive(),
        status="running",
        company_id=5,
        trigger="manual",
    )
    record.id = 901
    session = _FakeSession(get_map={(backup_service.BackupHistory, 901): record})

    class FakeProvider:
        async def save_file(self, source_path, destination_path):
            return destination_path

    monkeypatch.setattr(
        backup_service,
        "settings",
        SimpleNamespace(encryption_enabled=False, secondary_target_enabled=True),
    )
    monkeypatch.setattr(backup_service, "AsyncSessionLocal", _SessionFactory([session]))
    monkeypatch.setattr(
        backup_service.BackupService, "_run_pg_dump", _async_return(str(dump_path))
    )
    monkeypatch.setattr(
        backup_service.BackupService,
        "_get_yd_provider",
        staticmethod(_async_return(FakeProvider())),
    )
    monkeypatch.setattr(
        backup_service.BackupService, "_copy_to_secondary", _async_return(False)
    )
    monkeypatch.setattr(
        backup_service.BackupService, "_rotate_backups", _async_return(None)
    )
    monkeypatch.setattr(backup_service, "send_heartbeat", _async_return(True))
    monkeypatch.setattr(backup_service.asyncio, "to_thread", _fake_to_thread)

    try:
        result = await backup_service.BackupService().run_backup(
            session=session, company_id=5, yd_folder="daily", trigger="manual"
        )

        assert result.status == "success"
        assert result.target == "primary"
        # The path is recorded so the operator can see the copy is missing and
        # re-run it, rather than silently believing there are two copies.
        assert result.secondary_path == result.yd_path
    finally:
        for name in ("backup.dump", "backup.dump.gz"):
            leftover = temp_dir / name
            if leftover.exists():
                leftover.unlink()
        temp_dir.rmdir()


# ----------------------------------------------------------------------
# Alerting
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_failed_backup_pings_the_dead_mans_switch(monkeypatch):
    from app.services import backup_service

    temp_dir = Path(tempfile.mkdtemp(prefix="backup-heartbeat-"))
    dump_path = temp_dir / "backup.dump"
    dump_path.write_bytes(b"payload")

    record = backup_service.BackupHistory(
        started_at=backup_service._utcnow_naive(),
        status="running",
        company_id=5,
        trigger="manual",
    )
    record.id = 901
    session = _FakeSession(get_map={(backup_service.BackupHistory, 901): record})

    heartbeats: list[str] = []

    async def _fake_heartbeat(status="success", detail=""):
        heartbeats.append(status)
        return True

    monkeypatch.setattr(
        backup_service,
        "settings",
        SimpleNamespace(encryption_enabled=False, secondary_target_enabled=False),
    )
    monkeypatch.setattr(backup_service, "AsyncSessionLocal", _SessionFactory([session]))
    monkeypatch.setattr(
        backup_service.BackupService, "_run_pg_dump", _async_return(str(dump_path))
    )
    # No storage provider -> the run fails.
    monkeypatch.setattr(
        backup_service.BackupService,
        "_get_yd_provider",
        staticmethod(_async_return(None)),
    )
    monkeypatch.setattr(
        backup_service.BackupService, "_rotate_backups", _async_return(None)
    )
    monkeypatch.setattr(backup_service, "send_heartbeat", _fake_heartbeat)
    monkeypatch.setattr(backup_service.asyncio, "to_thread", _fake_to_thread)

    try:
        result = await backup_service.BackupService().run_backup(
            session=session, company_id=5, yd_folder="daily", trigger="manual"
        )

        assert result.status == "failed"
        assert result.duration_seconds is not None
        assert heartbeats == ["fail"]
    finally:
        for name in ("backup.dump", "backup.dump.gz"):
            leftover = temp_dir / name
            if leftover.exists():
                leftover.unlink()
        temp_dir.rmdir()


# ----------------------------------------------------------------------
# Rotation
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rotate_backups_uses_gfs_ladder_when_configured(monkeypatch):
    """With a ladder configured, a 6-week-old point must survive rotation.

    The series is anchored to a fixed date because the GFS decision depends
    only on the artifacts' own timestamps, never on "now" — which is exactly
    what makes the ladder reproducible.
    """
    from app.services import backup_service

    anchor = datetime(2026, 9, 14, 3, 0, 0)
    backups = [
        SimpleNamespace(
            id=index + 1,
            started_at=anchor - timedelta(days=index),
            yd_path=f"backups/{index}.sql.gz",
            company_id=9,
            status="success",
            secondary_path=None,
        )
        for index in range(60)
    ]

    settings_session = _FakeSession()
    list_session = _FakeSession(execute_results=[_FakeScalarsResult(backups)])
    delete_session = _FakeSession(
        get_map={(backup_service.BackupHistory, row.id): row for row in backups}
    )

    class FakeSettingsService:
        def __init__(self, _session):
            pass

        async def get_all_settings(self):
            return SimpleNamespace(
                backup=SimpleNamespace(
                    backup_retention_days=30,
                    backup_max_copies=30,
                    backup_keep_daily=7,
                    backup_keep_weekly=4,
                    backup_keep_monthly=12,
                    backup_keep_yearly=3,
                )
            )

    deleted_paths: list[str] = []

    class FakeProvider:
        async def delete_file(self, path):
            deleted_paths.append(path)

    monkeypatch.setattr(
        backup_service,
        "AsyncSessionLocal",
        _SessionFactory([settings_session, list_session, delete_session]),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "app.services.settings_service",
        SimpleNamespace(SettingsService=FakeSettingsService),
    )
    monkeypatch.setattr(
        backup_service.BackupService,
        "_get_yd_provider",
        staticmethod(_async_return(FakeProvider())),
    )

    await backup_service.BackupService()._rotate_backups(
        company_id=9, yd_folder="backups"
    )

    # Newest in the month that day 45 belongs to (day 45 is that month's last
    # day) -> retained by the monthly tier. The legacy rule (30 days) would
    # already have pruned it, which is the whole point of the ladder.
    assert "backups/45.sql.gz" not in deleted_paths
    # Same month, but not the newest point in it, and outside every other tier.
    assert "backups/59.sql.gz" in deleted_paths
    # Daily tier still guarantees the last week.
    for index in range(7):
        assert f"backups/{index}.sql.gz" not in deleted_paths
    # The ladder is bounded by 7+4+12+3 restore points.
    kept = 60 - len(deleted_paths)
    assert 7 <= kept <= 26


@pytest.mark.asyncio
async def test_rotate_backups_falls_back_to_legacy_rule_without_ladder(monkeypatch):
    from app.services import backup_service

    now = backup_service._utcnow_naive()
    backups = [
        SimpleNamespace(
            id=index + 1,
            started_at=now - timedelta(days=index),
            yd_path=f"backups/{index}.sql.gz",
            company_id=9,
            status="success",
            secondary_path=None,
        )
        for index in range(40)
    ]

    settings_session = _FakeSession()
    list_session = _FakeSession(execute_results=[_FakeScalarsResult(backups)])
    delete_session = _FakeSession(
        get_map={(backup_service.BackupHistory, row.id): row for row in backups}
    )

    class FakeSettingsService:
        def __init__(self, _session):
            pass

        async def get_all_settings(self):
            # Pre-GFS deployment: only the legacy knobs exist.
            return SimpleNamespace(
                backup=SimpleNamespace(
                    backup_retention_days=30,
                    backup_max_copies=30,
                )
            )

    deleted_paths: list[str] = []

    class FakeProvider:
        async def delete_file(self, path):
            deleted_paths.append(path)

    monkeypatch.setattr(
        backup_service,
        "AsyncSessionLocal",
        _SessionFactory([settings_session, list_session, delete_session]),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "app.services.settings_service",
        SimpleNamespace(SettingsService=FakeSettingsService),
    )
    monkeypatch.setattr(
        backup_service.BackupService,
        "_get_yd_provider",
        staticmethod(_async_return(FakeProvider())),
    )

    await backup_service.BackupService()._rotate_backups(
        company_id=9, yd_folder="backups"
    )

    # Legacy rule: everything at index >= max_copies or older than 30 days goes.
    assert deleted_paths == [f"backups/{index}.sql.gz" for index in range(30, 40)]


@pytest.mark.asyncio
async def test_rotate_backups_removes_the_secondary_copy_too(monkeypatch):
    from app.services import backup_service

    now = backup_service._utcnow_naive()
    stale = SimpleNamespace(
        id=1,
        started_at=now - timedelta(days=10),
        yd_path="backups/1.sql.gz",
        company_id=9,
        status="success",
        secondary_path="backups/1.sql.gz",
    )

    settings_session = _FakeSession()
    list_session = _FakeSession(execute_results=[_FakeScalarsResult([stale])])
    delete_session = _FakeSession(
        get_map={(backup_service.BackupHistory, 1): stale}
    )

    class FakeSettingsService:
        def __init__(self, _session):
            pass

        async def get_all_settings(self):
            return SimpleNamespace(
                backup=SimpleNamespace(
                    backup_retention_days=1, backup_max_copies=30
                )
            )

    class FakeProvider:
        def __init__(self):
            self.deleted = []

        async def delete_file(self, path):
            self.deleted.append(path)

    provider = FakeProvider()
    secondary_deleted: list[str] = []

    async def _fake_delete_secondary(self, remote_path):
        secondary_deleted.append(remote_path)

    monkeypatch.setattr(
        backup_service,
        "AsyncSessionLocal",
        _SessionFactory([settings_session, list_session, delete_session]),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "app.services.settings_service",
        SimpleNamespace(SettingsService=FakeSettingsService),
    )
    monkeypatch.setattr(
        backup_service.BackupService,
        "_get_yd_provider",
        staticmethod(_async_return(provider)),
    )
    monkeypatch.setattr(
        backup_service.BackupService, "_delete_from_secondary", _fake_delete_secondary
    )

    await backup_service.BackupService()._rotate_backups(
        company_id=9, yd_folder="backups"
    )

    assert provider.deleted == ["backups/1.sql.gz"]
    assert secondary_deleted == ["backups/1.sql.gz"]
    assert delete_session.deleted == [stale]


# ----------------------------------------------------------------------
# Integrity verification bookkeeping
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_backup_integrity_records_ok_status(monkeypatch):
    from app.services import backup_service

    payload = b"verified-payload"
    digest = hashlib.sha256(payload).hexdigest()

    record = backup_service.BackupHistory(
        started_at=backup_service._utcnow_naive(),
        status="success",
        company_id=5,
        trigger="manual",
    )
    record.id = 77
    record.checksum = digest
    record.yd_path = "daily/backup_x.sql.gz"
    record.encrypted = False

    session = _FakeSession(get_map={(backup_service.BackupHistory, 77): record})

    async def _fake_download(self, backup_id, dest_path):
        Path(dest_path).write_bytes(payload)
        return dest_path

    monkeypatch.setattr(backup_service, "AsyncSessionLocal", _SessionFactory([session]))
    monkeypatch.setattr(
        backup_service.BackupService, "download_backup", _fake_download
    )

    ok = await backup_service.BackupService().verify_backup_integrity(77)

    assert ok is True
    assert record.verification_status == "ok"
    assert record.verified_at is not None
    assert session.commit_calls == 1


@pytest.mark.asyncio
async def test_verify_backup_integrity_records_mismatch(monkeypatch):
    from app.services import backup_service

    record = backup_service.BackupHistory(
        started_at=backup_service._utcnow_naive(),
        status="success",
        company_id=5,
        trigger="manual",
    )
    record.id = 78
    record.checksum = "0" * 64
    record.yd_path = "daily/backup_y.sql.gz"
    record.encrypted = False

    session = _FakeSession(get_map={(backup_service.BackupHistory, 78): record})

    async def _fake_download(self, backup_id, dest_path):
        Path(dest_path).write_bytes(b"tampered")
        return dest_path

    monkeypatch.setattr(backup_service, "AsyncSessionLocal", _SessionFactory([session]))
    monkeypatch.setattr(
        backup_service.BackupService, "download_backup", _fake_download
    )

    ok = await backup_service.BackupService().verify_backup_integrity(78)

    assert ok is False
    assert record.verification_status == "checksum_mismatch"


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


class _FakeScalars:
    def __init__(self, values):
        self._values = list(values)

    def all(self):
        return list(self._values)


class _FakeScalarsResult:
    def __init__(self, values):
        self._values = list(values)

    def scalars(self):
        return _FakeScalars(self._values)


class _FakeSession:
    def __init__(self, get_map=None, execute_results=None):
        self.get_map = get_map or {}
        self.execute_results = list(execute_results or [])
        self.deleted = []
        self.commit_calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, model, pk):
        return self.get_map.get((model, pk))

    async def execute(self, _stmt):
        return self.execute_results.pop(0)

    async def delete(self, obj):
        self.deleted.append(obj)

    async def commit(self):
        self.commit_calls += 1

    async def rollback(self):
        return None

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = 901

    async def refresh(self, obj):
        return None


class _SessionFactory:
    def __init__(self, sessions):
        self._sessions = list(sessions)

    def __call__(self):
        return self._sessions.pop(0)


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner


async def _fake_to_thread(func, *args, **kwargs):
    return func(*args, **kwargs)
