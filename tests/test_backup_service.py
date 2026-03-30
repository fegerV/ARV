import gzip
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest


def test_gzip_file_compresses_source_bytes():
    from app.services.backup_service import BackupService

    temp_dir = _make_temp_dir()
    src = temp_dir / "backup.sql"
    dst = temp_dir / "backup.sql.gz"
    payload = ("select 1;\n" * 500).encode()
    src.write_bytes(payload)

    try:
        BackupService._gzip_file(str(src), str(dst))
        assert dst.exists()
        with gzip.open(dst, "rb") as fh:
            assert fh.read() == payload
    finally:
        for path in (dst, src):
            if path.exists():
                path.unlink()
        temp_dir.rmdir()


@pytest.mark.asyncio
async def test_get_yd_provider_returns_none_when_company_missing(monkeypatch):
    from app.services import backup_service

    session = _FakeSession(get_map={})
    monkeypatch.setattr(backup_service, "AsyncSessionLocal", _SessionFactory([session]))

    result = await backup_service.BackupService._get_yd_provider(7)

    assert result is None


@pytest.mark.asyncio
async def test_get_yd_provider_returns_only_yandex_provider(monkeypatch):
    from app.services import backup_service

    company = SimpleNamespace(id=5, name="Vertex")
    session = _FakeSession(get_map={(backup_service.Company, 5): company})

    class FakeYandexProvider:
        pass

    monkeypatch.setattr(backup_service, "YandexDiskStorageProvider", FakeYandexProvider)
    monkeypatch.setattr(
        backup_service,
        "get_provider_for_company",
        _async_return(FakeYandexProvider()),
    )
    monkeypatch.setattr(backup_service, "AsyncSessionLocal", _SessionFactory([session]))

    result = await backup_service.BackupService._get_yd_provider(5)

    assert isinstance(result, FakeYandexProvider)


@pytest.mark.asyncio
async def test_get_yd_provider_returns_none_for_non_yandex_provider(monkeypatch):
    from app.services import backup_service

    company = SimpleNamespace(id=6, name="Vertex")
    session = _FakeSession(get_map={(backup_service.Company, 6): company})

    class FakeOtherProvider:
        pass

    monkeypatch.setattr(
        backup_service,
        "get_provider_for_company",
        _async_return(FakeOtherProvider()),
    )
    monkeypatch.setattr(backup_service, "AsyncSessionLocal", _SessionFactory([session]))

    result = await backup_service.BackupService._get_yd_provider(6)

    assert result is None


@pytest.mark.asyncio
async def test_delete_backup_returns_false_for_missing_record():
    from app.services.backup_service import BackupService, BackupHistory

    session = _FakeSession(get_map={(BackupHistory, 101): None})

    result = await BackupService().delete_backup(session, 101)

    assert result is False
    assert session.deleted == []
    assert session.commit_calls == 0


@pytest.mark.asyncio
async def test_delete_backup_deletes_record_even_if_provider_delete_fails(monkeypatch):
    from app.services import backup_service

    record = SimpleNamespace(id=8, yd_path="backups/file.sql.gz", company_id=4)
    session = _FakeSession(get_map={(backup_service.BackupHistory, 8): record})

    class FakeProvider:
        async def delete_file(self, _path):
            raise RuntimeError("boom")

    monkeypatch.setattr(
        backup_service.BackupService,
        "_get_yd_provider",
        staticmethod(_async_return(FakeProvider())),
    )

    result = await backup_service.BackupService().delete_backup(session, 8)

    assert result is True
    assert session.deleted == [record]
    assert session.commit_calls == 1


@pytest.mark.asyncio
async def test_rotate_backups_deletes_old_and_excess_records(monkeypatch):
    from app.services import backup_service

    now = backup_service._utcnow_naive()
    backups = [
        SimpleNamespace(id=1, started_at=now - timedelta(days=1), yd_path="backups/1.sql.gz", company_id=9, status="success"),
        SimpleNamespace(id=2, started_at=now - timedelta(days=2), yd_path="backups/2.sql.gz", company_id=9, status="success"),
        SimpleNamespace(id=3, started_at=now - timedelta(days=10), yd_path="backups/3.sql.gz", company_id=9, status="success"),
    ]

    settings_session = _FakeSession()
    list_session = _FakeSession(execute_results=[_FakeScalarsResult(backups)])
    delete_session = _FakeSession(
        get_map={
            (backup_service.BackupHistory, 2): backups[1],
            (backup_service.BackupHistory, 3): backups[2],
        }
    )

    class FakeSettingsService:
        def __init__(self, _session):
            pass

        async def get_all_settings(self):
                return SimpleNamespace(
                    backup=SimpleNamespace(
                        backup_retention_days=7,
                        backup_max_copies=1,
                    )
                )

    deleted_paths = []

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

    await backup_service.BackupService()._rotate_backups(company_id=9, yd_folder="backups")

    assert deleted_paths == ["backups/2.sql.gz", "backups/3.sql.gz"]
    assert delete_session.deleted == [backups[1], backups[2]]
    assert delete_session.commit_calls == 1


@pytest.mark.asyncio
async def test_rotate_backups_returns_early_when_nothing_to_delete(monkeypatch):
    from app.services import backup_service

    now = backup_service._utcnow_naive()
    backups = [
        SimpleNamespace(id=1, started_at=now - timedelta(days=1), yd_path="backups/1.sql.gz", company_id=9, status="success"),
    ]

    settings_session = _FakeSession()
    list_session = _FakeSession(execute_results=[_FakeScalarsResult(backups)])

    class FakeSettingsService:
        def __init__(self, _session):
            pass

        async def get_all_settings(self):
            return SimpleNamespace(
                backup=SimpleNamespace(
                    backup_retention_days=30,
                    backup_max_copies=5,
                )
            )

    monkeypatch.setattr(
        backup_service,
        "AsyncSessionLocal",
        _SessionFactory([settings_session, list_session]),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "app.services.settings_service",
        SimpleNamespace(SettingsService=FakeSettingsService),
    )

    await backup_service.BackupService()._rotate_backups(company_id=9, yd_folder="backups")


@pytest.mark.asyncio
async def test_rotate_backups_skips_missing_records_and_swallows_provider_delete_errors(monkeypatch):
    from app.services import backup_service

    now = backup_service._utcnow_naive()
    stale = SimpleNamespace(
        id=10,
        started_at=now - timedelta(days=20),
        yd_path="backups/10.sql.gz",
        company_id=9,
        status="success",
    )
    another = SimpleNamespace(
        id=11,
        started_at=now - timedelta(days=15),
        yd_path="backups/11.sql.gz",
        company_id=9,
        status="success",
    )

    settings_session = _FakeSession()
    list_session = _FakeSession(execute_results=[_FakeScalarsResult([stale, another])])
    delete_session = _FakeSession(
        get_map={
            (backup_service.BackupHistory, 10): None,
            (backup_service.BackupHistory, 11): another,
        }
    )

    class FakeSettingsService:
        def __init__(self, _session):
            pass

        async def get_all_settings(self):
            return SimpleNamespace(
                backup=SimpleNamespace(
                    backup_retention_days=7,
                    backup_max_copies=5,
                )
            )

    class FakeProvider:
        def __init__(self):
            self.deleted = []

        async def delete_file(self, path):
            self.deleted.append(path)
            raise RuntimeError("boom")

    provider = FakeProvider()

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

    await backup_service.BackupService()._rotate_backups(company_id=9, yd_folder="backups")

    assert provider.deleted == ["backups/11.sql.gz"]
    assert delete_session.deleted == [another]
    assert delete_session.commit_calls == 1


@pytest.mark.asyncio
async def test_run_pg_dump_returns_temp_file_on_success(monkeypatch):
    from app.services import backup_service

    temp_dir = _make_temp_dir()
    dump_path = temp_dir / "dump.sql"
    dump_path.write_text("select 1;")

    class FakeNamedTempFile:
        name = str(dump_path)

        def close(self):
            return None

    class FakeProcess:
        returncode = 0

        async def communicate(self):
            return b"", b""

    async def _fake_create_subprocess_exec(*cmd, **kwargs):
        assert cmd[0] == "pg_dump"
        assert "-f" in cmd
        assert kwargs["env"]["PGPASSWORD"] == "secret"
        return FakeProcess()

    async def _fake_wait_for(awaitable, timeout):
        return await awaitable

    monkeypatch.setattr(
        backup_service,
        "settings",
        SimpleNamespace(DATABASE_URL="postgresql+asyncpg://postgres:secret@db:5432/appdb"),
    )
    monkeypatch.setattr(backup_service.tempfile, "NamedTemporaryFile", lambda suffix, delete: FakeNamedTempFile())
    monkeypatch.setattr(backup_service.asyncio, "create_subprocess_exec", _fake_create_subprocess_exec)
    monkeypatch.setattr(backup_service.asyncio, "wait_for", _fake_wait_for)

    try:
        result = await backup_service.BackupService()._run_pg_dump()
        assert result == str(dump_path)
    finally:
        if dump_path.exists():
            dump_path.unlink()
        temp_dir.rmdir()


@pytest.mark.asyncio
async def test_run_pg_dump_raises_on_nonzero_exit(monkeypatch):
    from app.services import backup_service

    temp_dir = _make_temp_dir()
    dump_path = temp_dir / "dump.sql"
    dump_path.write_text("partial dump")

    class FakeNamedTempFile:
        name = str(dump_path)

        def close(self):
            return None

    class FakeProcess:
        returncode = 2

        async def communicate(self):
            return b"", b"permission denied"

    monkeypatch.setattr(
        backup_service,
        "settings",
        SimpleNamespace(DATABASE_URL="postgresql://postgres:secret@db/appdb"),
    )
    monkeypatch.setattr(backup_service.tempfile, "NamedTemporaryFile", lambda suffix, delete: FakeNamedTempFile())
    monkeypatch.setattr(backup_service.asyncio, "create_subprocess_exec", _async_return(FakeProcess()))
    monkeypatch.setattr(backup_service.asyncio, "wait_for", _pass_through_wait_for)

    with pytest.raises(RuntimeError) as exc_info:
        await backup_service.BackupService()._run_pg_dump()

    assert "pg_dump exited with code 2" in str(exc_info.value)
    assert dump_path.exists() is False
    temp_dir.rmdir()


@pytest.mark.asyncio
async def test_run_pg_dump_kills_process_on_timeout(monkeypatch):
    from app.services import backup_service

    temp_dir = _make_temp_dir()
    dump_path = temp_dir / "dump.sql"
    dump_path.write_text("partial dump")

    class FakeNamedTempFile:
        name = str(dump_path)

        def close(self):
            return None

    class FakeProcess:
        returncode = None

        def __init__(self):
            self.killed = False
            self.waited = False

        async def communicate(self):
            return b"", b""

        def kill(self):
            self.killed = True

        async def wait(self):
            self.waited = True

    process = FakeProcess()

    async def _raise_timeout(awaitable, timeout):
        close = getattr(awaitable, "close", None)
        if callable(close):
            close()
        raise backup_service.asyncio.TimeoutError()

    monkeypatch.setattr(
        backup_service,
        "settings",
        SimpleNamespace(DATABASE_URL="postgresql://postgres:secret@db/appdb"),
    )
    monkeypatch.setattr(backup_service.tempfile, "NamedTemporaryFile", lambda suffix, delete: FakeNamedTempFile())
    monkeypatch.setattr(backup_service.asyncio, "create_subprocess_exec", _async_return(process))
    monkeypatch.setattr(backup_service.asyncio, "wait_for", _raise_timeout)

    with pytest.raises(RuntimeError) as exc_info:
        await backup_service.BackupService()._run_pg_dump()

    assert "pg_dump timed out" in str(exc_info.value)
    assert process.killed is True
    assert process.waited is True
    assert dump_path.exists() is False
    temp_dir.rmdir()


@pytest.mark.asyncio
async def test_run_backup_success_updates_record_and_cleans_files(monkeypatch):
    from app.services import backup_service

    temp_dir = _make_temp_dir()
    dump_path = temp_dir / "backup.sql"
    dump_bytes = b"select 1;\n" * 20
    dump_path.write_bytes(dump_bytes)

    created_record = backup_service.BackupHistory(
        started_at=backup_service._utcnow_naive(),
        status="running",
        company_id=5,
        trigger="manual",
    )
    created_record.id = 901

    create_session = _FakeSession(shared_record=created_record)
    update_session = _FakeSession(get_map={(backup_service.BackupHistory, 901): created_record}, shared_record=created_record)
    result_session = _FakeSession(get_map={(backup_service.BackupHistory, 901): created_record}, shared_record=created_record)

    class FakeProvider:
        def __init__(self):
            self.saved = []

        async def save_file_bytes(self, data, path):
            self.saved.append((data, path))

    provider = FakeProvider()

    async def _fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    rotated = []

    async def _fake_rotate_backups(self, company_id, yd_folder):
        rotated.append((company_id, yd_folder))

    monkeypatch.setattr(backup_service, "AsyncSessionLocal", _SessionFactory([create_session, update_session, result_session]))
    monkeypatch.setattr(backup_service.BackupService, "_run_pg_dump", _async_return(str(dump_path)))
    monkeypatch.setattr(
        backup_service.BackupService,
        "_get_yd_provider",
        staticmethod(_async_return(provider)),
    )
    monkeypatch.setattr(backup_service.asyncio, "to_thread", _fake_to_thread)
    monkeypatch.setattr(backup_service.BackupService, "_rotate_backups", _fake_rotate_backups)

    result = await backup_service.BackupService().run_backup(company_id=5, yd_folder="daily", trigger="manual")

    assert result is created_record
    assert created_record.id == 901
    assert created_record.status == "success"
    assert created_record.size_bytes is not None
    assert created_record.yd_path is not None
    assert created_record.yd_path.startswith("daily/backup_")
    assert provider.saved[0][0].startswith(b"\x1f\x8b")
    assert provider.saved[0][1] == created_record.yd_path
    assert rotated == [(5, "daily")]
    assert dump_path.exists() is False
    assert (temp_dir / "backup.sql.gz").exists() is False
    temp_dir.rmdir()


@pytest.mark.asyncio
async def test_run_backup_failure_marks_record_failed_and_cleans_files(monkeypatch):
    from app.services import backup_service

    temp_dir = _make_temp_dir()
    dump_path = temp_dir / "backup.sql"
    dump_path.write_bytes(b"select 1;")

    created_record = backup_service.BackupHistory(
        started_at=backup_service._utcnow_naive(),
        status="running",
        company_id=5,
        trigger="manual",
    )
    created_record.id = 901

    create_session = _FakeSession(shared_record=created_record)
    fail_session = _FakeSession(get_map={(backup_service.BackupHistory, 901): created_record}, shared_record=created_record)
    result_session = _FakeSession(get_map={(backup_service.BackupHistory, 901): created_record}, shared_record=created_record)

    async def _fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(backup_service, "AsyncSessionLocal", _SessionFactory([create_session, fail_session, result_session]))
    monkeypatch.setattr(backup_service.BackupService, "_run_pg_dump", _async_return(str(dump_path)))
    monkeypatch.setattr(
        backup_service.BackupService,
        "_get_yd_provider",
        staticmethod(_async_return(None)),
    )
    monkeypatch.setattr(backup_service.asyncio, "to_thread", _fake_to_thread)
    monkeypatch.setattr(backup_service.BackupService, "_rotate_backups", _async_return(None))

    result = await backup_service.BackupService().run_backup(company_id=5, yd_folder="daily", trigger="manual")

    assert result is created_record
    assert created_record.status == "failed"
    assert "Yandex Disk provider not available" in created_record.error_message
    assert dump_path.exists() is False
    assert (temp_dir / "backup.sql.gz").exists() is False
    temp_dir.rmdir()


@pytest.mark.asyncio
async def test_run_backup_logs_rotation_warning_but_returns_record(monkeypatch):
    from app.services import backup_service

    created_record = backup_service.BackupHistory(
        started_at=backup_service._utcnow_naive(),
        status="running",
        company_id=5,
        trigger="manual",
    )
    created_record.id = 901

    create_session = _FakeSession(shared_record=created_record)
    fail_session = _FakeSession(get_map={(backup_service.BackupHistory, 901): created_record}, shared_record=created_record)
    result_session = _FakeSession(get_map={(backup_service.BackupHistory, 901): created_record}, shared_record=created_record)

    warnings = []

    class FakeLog:
        def info(self, *args, **kwargs):
            return None

        def error(self, *args, **kwargs):
            return None

        def warning(self, event, **kwargs):
            warnings.append((event, kwargs))

    monkeypatch.setattr(backup_service, "AsyncSessionLocal", _SessionFactory([create_session, fail_session, result_session]))
    monkeypatch.setattr(backup_service.BackupService, "_run_pg_dump", _async_return(None))
    monkeypatch.setattr(backup_service.BackupService, "_rotate_backups", _async_raise(RuntimeError("rotate failed")))
    monkeypatch.setattr(backup_service.logger, "bind", lambda **kwargs: FakeLog())

    result = await backup_service.BackupService().run_backup(company_id=5, yd_folder="daily", trigger="manual")

    assert result is created_record
    assert created_record.status == "failed"
    assert warnings == [("backup_rotation_failed", {"error": "rotate failed"})]


@pytest.mark.asyncio
async def test_list_backups_returns_scalar_rows():
    from app.services.backup_service import BackupService

    backup1 = SimpleNamespace(id=1)
    backup2 = SimpleNamespace(id=2)
    session = _FakeSession(execute_results=[_FakeScalarsResult([backup1, backup2])])

    result = await BackupService().list_backups(session, limit=5, offset=10)

    assert result == [backup1, backup2]


@pytest.mark.asyncio
async def test_get_last_status_returns_scalar_or_none():
    from app.services.backup_service import BackupService

    latest = SimpleNamespace(id=3, status="success")
    session = _FakeSession(execute_results=[_FakeScalarOneOrNoneResult(latest)])

    result = await BackupService().get_last_status(session)

    assert result is latest


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


class _FakeScalarOneOrNoneResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeSession:
    def __init__(self, get_map=None, execute_results=None, shared_record=None):
        self.get_map = get_map or {}
        self.execute_results = list(execute_results or [])
        self.deleted = []
        self.commit_calls = 0
        self.shared_record = shared_record

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

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = 901
        self.shared_record = obj

    async def refresh(self, obj):
        self.shared_record = obj


class _SessionFactory:
    def __init__(self, sessions):
        self._sessions = list(sessions)

    def __call__(self):
        return self._sessions.pop(0)


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner


def _async_raise(exc):
    async def _inner(*args, **kwargs):
        raise exc

    return _inner


async def _pass_through_wait_for(awaitable, timeout):
    return await awaitable


def _make_temp_dir() -> Path:
    root = Path("e:/Project/ARV/.pytest-temp") / f"backup-service-{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root
