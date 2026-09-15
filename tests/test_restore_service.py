"""Tests for ``app/services/restore_service.py``.

The service exists because a byte-perfect artifact can still be unrestorable.
These tests cover the three levels of proof: materialisation, archive listing,
and the drill into a throwaway database.
"""

import gzip
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest


def _restore_settings(**overrides) -> SimpleNamespace:
    base = {
        "DATABASE_URL": "postgresql+asyncpg://arv:secret@db:5432/vertex_ar",
        "BACKUP_AGE_BINARY": "age",
        "BACKUP_AGE_IDENTITY_FILE": "/etc/arv/backup-age.key",
        "BACKUP_PG_RESTORE_BINARY": "pg_restore",
        "BACKUP_PSQL_BINARY": "psql",
        "BACKUP_RESTORE_JOBS": 4,
        "BACKUP_DRILL_DB_PREFIX": "arv_drill",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _record(**overrides) -> SimpleNamespace:
    base = {
        "id": 77,
        "encrypted": False,
        "yd_path": "daily/backup_20260914_030000.sql.gz",
        "backup_type": "db",
        "verified_at": None,
        "verification_status": None,
        "restore_tested_at": None,
        "restore_test_status": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


# ----------------------------------------------------------------------
# Level 1: materialisation
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_materialize_dump_downloads_and_decompresses(monkeypatch):
    from app.services import restore_service
    from app.services.backup_service import BackupService

    payload = b"custom-format-archive-bytes"

    async def _fake_download(self, backup_id, dest_path):
        with gzip.open(dest_path, "wb") as handle:
            handle.write(payload)
        return dest_path

    session = _FakeSession(get_map={(restore_service.BackupHistory, 77): _record()})

    monkeypatch.setattr(restore_service, "settings", _restore_settings())
    monkeypatch.setattr(restore_service, "AsyncSessionLocal", _sticky_factory(session))
    monkeypatch.setattr(BackupService, "download_backup", _fake_download)

    workdir = tempfile.mkdtemp(prefix="arv-materialize-")
    try:
        dump_path = await restore_service.RestoreService().materialize_dump(77, workdir)

        assert dump_path.endswith(".dump")
        assert Path(dump_path).read_bytes() == payload
        assert os.path.basename(dump_path) == "backup_77.dump"
        # The downloaded artifact keeps the stored name for traceability.
        assert (Path(workdir) / "backup_20260914_030000.sql.gz").exists()
    finally:
        _rmtree(workdir)


@pytest.mark.asyncio
async def test_materialize_dump_decrypts_with_the_age_identity(monkeypatch):
    from app.services import restore_service
    from app.services.backup_service import BackupService

    encrypted_payload = b"-----BEGIN AGE ENCRYPTED FILE-----\nfake\n"

    async def _fake_download(self, backup_id, dest_path):
        Path(dest_path).write_bytes(encrypted_payload)
        return dest_path

    async def _fake_run_command(cmd, **kwargs):
        # age --decrypt ... --output <gz> <src>
        out_index = cmd.index("--output") + 1
        with gzip.open(cmd[out_index], "wb") as handle:
            handle.write(b"decrypted-archive")
        return ""

    record = _record(
        encrypted=True,
        yd_path="daily/backup_20260914_030000.sql.gz.age",
    )
    session = _FakeSession(get_map={(restore_service.BackupHistory, 77): record})

    identity_dir = tempfile.mkdtemp(prefix="arv-age-key-")
    identity_path = Path(identity_dir) / "backup-age.key"
    identity_path.write_text("AGE-SECRET-KEY-1FAKEIDENTITY\n")

    monkeypatch.setattr(
        restore_service,
        "settings",
        _restore_settings(BACKUP_AGE_IDENTITY_FILE=str(identity_path)),
    )
    monkeypatch.setattr(restore_service, "AsyncSessionLocal", _sticky_factory(session))
    monkeypatch.setattr(BackupService, "download_backup", _fake_download)
    monkeypatch.setattr(restore_service, "run_command", _fake_run_command)

    workdir = tempfile.mkdtemp(prefix="arv-materialize-enc-")
    try:
        dump_path = await restore_service.RestoreService().materialize_dump(77, workdir)

        assert Path(dump_path).read_bytes() == b"decrypted-archive"
        # The decrypted intermediate is named after the artifact, minus .age.
        assert (Path(workdir) / "backup_20260914_030000.sql.gz").exists()
    finally:
        _rmtree(workdir)
        _rmtree(identity_dir)


@pytest.mark.asyncio
async def test_materialize_encrypted_dump_without_identity_fails_loudly(monkeypatch):
    from app.services import restore_service
    from app.services.backup_service import BackupService

    async def _fake_download(self, backup_id, dest_path):
        Path(dest_path).write_bytes(b"ciphertext")
        return dest_path

    record = _record(
        encrypted=True, yd_path="daily/backup_20260914_030000.sql.gz.age"
    )
    session = _FakeSession(get_map={(restore_service.BackupHistory, 77): record})

    monkeypatch.setattr(
        restore_service, "settings", _restore_settings(BACKUP_AGE_IDENTITY_FILE="")
    )
    monkeypatch.setattr(restore_service, "AsyncSessionLocal", _sticky_factory(session))
    monkeypatch.setattr(BackupService, "download_backup", _fake_download)

    workdir = tempfile.mkdtemp(prefix="arv-materialize-noident-")
    try:
        with pytest.raises(RuntimeError, match="BACKUP_AGE_IDENTITY_FILE"):
            await restore_service.RestoreService().materialize_dump(77, workdir)
    finally:
        _rmtree(workdir)


@pytest.mark.asyncio
async def test_materialize_dump_rejects_a_missing_backup(monkeypatch):
    from app.services import restore_service

    session = _FakeSession(get_map={})

    monkeypatch.setattr(restore_service, "settings", _restore_settings())
    monkeypatch.setattr(restore_service, "AsyncSessionLocal", _sticky_factory(session))

    workdir = tempfile.mkdtemp(prefix="arv-materialize-missing-")
    try:
        with pytest.raises(RuntimeError, match="not found"):
            await restore_service.RestoreService().materialize_dump(999, workdir)
    finally:
        _rmtree(workdir)


# ----------------------------------------------------------------------
# Level 2: archive listing
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_dump_counts_entries_from_pg_restore_list(monkeypatch):
    from app.services import restore_service

    listing = "\n".join(
        [
            ";",
            "; Archive created at 2026-09-14 03:00:00 UTC",
            ";",
            "3; 2615 2200 SCHEMA - public arv",
            "200; 1259 16385 TABLE public companies arv",
            "201; 1259 16390 TABLE public ar_contx arv",
            "202; 0 0 TABLE DATA public companies arv",
            "203; 0 0 TABLE DATA public ar_content arv",
        ]
    )

    record = _record()
    session = _FakeSession(get_map={(restore_service.BackupHistory, 77): record})

    async def _fake_materialize(self, backup_id, workdir):
        path = Path(workdir) / "backup.dump"
        path.write_bytes(b"archive")
        return str(path)

    captured: dict = {}

    async def _fake_run_command(cmd, **kwargs):
        captured["cmd"] = cmd
        return listing

    monkeypatch.setattr(restore_service, "settings", _restore_settings())
    monkeypatch.setattr(restore_service, "AsyncSessionLocal", _sticky_factory(session))
    monkeypatch.setattr(restore_service, "binary_available", lambda _b: True)
    monkeypatch.setattr(restore_service.RestoreService, "materialize_dump", _fake_materialize)
    monkeypatch.setattr(restore_service, "run_command", _fake_run_command)

    report = await restore_service.RestoreService().verify_dump(77)

    assert report["ok"] is True
    assert report["entries"] == 5  # comment lines are excluded
    assert report["tables"] == 4
    assert captured["cmd"][1] == "--list"
    assert record.verification_status == "ok"
    assert record.verified_at is not None


@pytest.mark.asyncio
async def test_verify_dump_records_failure_when_materialisation_breaks(monkeypatch):
    from app.services import restore_service

    record = _record()
    session = _FakeSession(get_map={(restore_service.BackupHistory, 77): record})

    async def _boom(self, backup_id, workdir):
        raise RuntimeError("truncated archive")

    monkeypatch.setattr(restore_service, "settings", _restore_settings())
    monkeypatch.setattr(restore_service, "AsyncSessionLocal", _sticky_factory(session))
    monkeypatch.setattr(restore_service, "binary_available", lambda _b: True)
    monkeypatch.setattr(restore_service.RestoreService, "materialize_dump", _boom)

    report = await restore_service.RestoreService().verify_dump(77)

    assert report["ok"] is False
    assert "truncated archive" in report["error"]
    assert record.verification_status == "list_failed"


@pytest.mark.asyncio
async def test_verify_dump_reports_missing_binary(monkeypatch):
    from app.services import restore_service

    monkeypatch.setattr(restore_service, "settings", _restore_settings())
    monkeypatch.setattr(restore_service, "binary_available", lambda _b: False)

    report = await restore_service.RestoreService().verify_dump(77)

    assert report["ok"] is False
    assert "pg_restore" in report["error"]


# ----------------------------------------------------------------------
# Level 3: drill and real restore
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_restore_drill_restores_into_a_throwaway_database(monkeypatch):
    from app.services import restore_service

    record = _record()
    session = _FakeSession(get_map={(restore_service.BackupHistory, 77): record})

    created: list[str] = []
    dropped: list[str] = []
    restored: list[tuple[str, str]] = []

    async def _fake_materialize(self, backup_id, workdir):
        path = Path(workdir) / "backup.dump"
        path.write_bytes(b"archive")
        return str(path)

    async def _fake_create(self, name):
        created.append(name)

    async def _fake_drop(self, name):
        dropped.append(name)

    async def _fake_restore_into(self, database, dump_path):
        restored.append((database, dump_path))

    async def _fake_count(self, database):
        return 14

    monkeypatch.setattr(restore_service, "settings", _restore_settings())
    monkeypatch.setattr(restore_service, "AsyncSessionLocal", _sticky_factory(session))
    monkeypatch.setattr(restore_service.RestoreService, "materialize_dump", _fake_materialize)
    monkeypatch.setattr(restore_service.RestoreService, "_create_database", _fake_create)
    monkeypatch.setattr(restore_service.RestoreService, "_drop_database", _fake_drop)
    monkeypatch.setattr(
        restore_service.RestoreService, "_pg_restore_into", _fake_restore_into
    )
    monkeypatch.setattr(restore_service.RestoreService, "_count_tables", _fake_count)

    report = await restore_service.RestoreService().restore_drill(77)

    assert report["ok"] is True
    assert report["tables_restored"] == 14
    assert len(created) == 1
    assert created[0].startswith("arv_drill_")
    assert restored[0][0] == created[0]
    # The throwaway database must never outlive the drill.
    assert dropped == created
    assert record.restore_test_status == "ok"
    assert record.restore_tested_at is not None


@pytest.mark.asyncio
async def test_restore_drill_drops_the_database_even_when_restore_fails(monkeypatch):
    from app.services import restore_service

    record = _record()
    session = _FakeSession(get_map={(restore_service.BackupHistory, 77): record})

    dropped: list[str] = []

    async def _fake_materialize(self, backup_id, workdir):
        path = Path(workdir) / "backup.dump"
        path.write_bytes(b"archive")
        return str(path)

    async def _fake_create(self, name):
        return None

    async def _fake_drop(self, name):
        dropped.append(name)

    async def _boom(self, database, dump_path):
        raise RuntimeError("pg_restore exited with code 1: relation already exists")

    monkeypatch.setattr(restore_service, "settings", _restore_settings())
    monkeypatch.setattr(restore_service, "AsyncSessionLocal", _sticky_factory(session))
    monkeypatch.setattr(restore_service.RestoreService, "materialize_dump", _fake_materialize)
    monkeypatch.setattr(restore_service.RestoreService, "_create_database", _fake_create)
    monkeypatch.setattr(restore_service.RestoreService, "_drop_database", _fake_drop)
    monkeypatch.setattr(restore_service.RestoreService, "_pg_restore_into", _boom)

    report = await restore_service.RestoreService().restore_drill(77)

    assert report["ok"] is False
    assert dropped and dropped[0].startswith("arv_drill_")
    assert record.restore_test_status == "restore_failed"


@pytest.mark.asyncio
async def test_restore_drill_fails_when_no_tables_came_back(monkeypatch):
    from app.services import restore_service

    record = _record()
    session = _FakeSession(get_map={(restore_service.BackupHistory, 77): record})

    async def _fake_materialize(self, backup_id, workdir):
        path = Path(workdir) / "backup.dump"
        path.write_bytes(b"archive")
        return str(path)

    async def _noop(self, *args):
        return None

    async def _zero(self, database):
        return 0

    monkeypatch.setattr(restore_service, "settings", _restore_settings())
    monkeypatch.setattr(restore_service, "AsyncSessionLocal", _sticky_factory(session))
    monkeypatch.setattr(restore_service.RestoreService, "materialize_dump", _fake_materialize)
    monkeypatch.setattr(restore_service.RestoreService, "_create_database", _noop)
    monkeypatch.setattr(restore_service.RestoreService, "_drop_database", _noop)
    monkeypatch.setattr(restore_service.RestoreService, "_pg_restore_into", _noop)
    monkeypatch.setattr(restore_service.RestoreService, "_count_tables", _zero)

    report = await restore_service.RestoreService().restore_drill(77)

    assert report["ok"] is False
    assert record.restore_test_status == "restore_failed"


@pytest.mark.asyncio
async def test_restore_to_refuses_to_overwrite_the_live_database(monkeypatch):
    from app.services import restore_service

    monkeypatch.setattr(restore_service, "settings", _restore_settings())

    with pytest.raises(RuntimeError, match="Refusing to restore over the live database"):
        await restore_service.RestoreService().restore_to(77, "vertex_ar")


@pytest.mark.asyncio
async def test_restore_to_rejects_unsafe_database_names(monkeypatch):
    from app.services import restore_service

    monkeypatch.setattr(restore_service, "settings", _restore_settings())

    with pytest.raises(ValueError, match="Unsafe target database name"):
        await restore_service.RestoreService().restore_to(
            77, 'vertex_ar"; DROP DATABASE vertex_ar; --'
        )


@pytest.mark.asyncio
async def test_restore_to_restores_into_a_separate_database(monkeypatch):
    from app.services import restore_service

    restored: list[tuple[str, str]] = []

    async def _fake_materialize(self, backup_id, workdir):
        path = Path(workdir) / "backup.dump"
        path.write_bytes(b"archive")
        return str(path)

    async def _fake_restore_into(self, database, dump_path):
        restored.append((database, dump_path))

    async def _fake_count(self, database):
        return 14

    monkeypatch.setattr(restore_service, "settings", _restore_settings())
    monkeypatch.setattr(restore_service.RestoreService, "materialize_dump", _fake_materialize)
    monkeypatch.setattr(
        restore_service.RestoreService, "_pg_restore_into", _fake_restore_into
    )
    monkeypatch.setattr(restore_service.RestoreService, "_count_tables", _fake_count)

    report = await restore_service.RestoreService().restore_to(77, "vertex_ar_recovered")

    assert report["ok"] is True
    assert report["tables_restored"] == 14
    assert restored[0][0] == "vertex_ar_recovered"


def test_drill_database_names_are_safe_identifiers(monkeypatch):
    from app.services import restore_service

    monkeypatch.setattr(restore_service, "settings", _restore_settings())

    name = restore_service.RestoreService._drill_db_name()

    assert restore_service._IDENTIFIER_RE.match(name)
    assert name.startswith("arv_drill_")


def test_drill_database_name_falls_back_when_prefix_is_unsafe(monkeypatch):
    from app.services import restore_service

    monkeypatch.setattr(
        restore_service,
        "settings",
        _restore_settings(BACKUP_DRILL_DB_PREFIX='bad"; DROP DATABASE x; --'),
    )

    name = restore_service.RestoreService._drill_db_name()

    assert name.startswith("arv_drill_")


def test_pg_restore_uses_parallelism_and_exit_on_error(monkeypatch):
    """A drill that tolerates errors proves nothing."""
    from app.services import restore_service

    captured: dict = {}

    async def _fake_run_command(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs.get("env")
        return ""

    monkeypatch.setattr(restore_service, "settings", _restore_settings())
    monkeypatch.setattr(restore_service, "run_command", _fake_run_command)

    import asyncio

    asyncio.run(
        restore_service.RestoreService()._pg_restore_into("drill_db", "/tmp/backup.dump")
    )

    cmd = captured["cmd"]
    assert cmd[0] == "pg_restore"
    assert "-j" in cmd and cmd[cmd.index("-j") + 1] == "4"
    assert "--exit-on-error" in cmd
    assert "--no-owner" in cmd
    assert cmd[-1] == "/tmp/backup.dump"
    assert captured["env"]["PGPASSWORD"] == "secret"


def test_pg_restore_does_not_replay_object_ownership(monkeypatch):
    """Restoring must not try to reassign objects to their original owner.

    A dump records each object's owner and pg_restore replays it as
    ``ALTER ... OWNER TO <role>``, which requires the restoring role to be able
    to ``SET ROLE`` to that role. Production has five objects owned by
    ``postgres`` (``ai_jobs`` and its sequence/indexes) while the application
    connects as ``vertex_ar``, so the replay failed with

        ERROR: must be able to SET ROLE "postgres"

    and ``--exit-on-error`` then aborted the entire restore, leaving the target
    database empty. Verified against the real cluster: with ``--no-owner`` the
    same dump restores all 15 tables; without it, one.
    """
    from app.services import restore_service

    captured: dict = {}

    async def _fake_run_command(cmd, **kwargs):
        captured["cmd"] = cmd
        return ""

    monkeypatch.setattr(restore_service, "settings", _restore_settings())
    monkeypatch.setattr(restore_service, "run_command", _fake_run_command)

    import asyncio

    asyncio.run(
        restore_service.RestoreService()._pg_restore_into("target_db", "/tmp/b.dump")
    )

    assert "--no-owner" in captured["cmd"]


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


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


def _sticky_factory(session):
    return lambda: session


def _rmtree(path: str) -> None:
    import shutil

    shutil.rmtree(path, ignore_errors=True)
