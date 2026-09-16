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


@pytest.mark.asyncio
async def test_verify_dump_skips_when_encrypted_and_the_identity_is_absent(
    monkeypatch, tmp_path
):
    """Encrypted + no key on the host is ``skipped``, not ``failed``.

    The age identity is deliberately kept off the production host, so the weekly
    verify timer can never open an encrypted dump there. Calling that a failure
    would make the timer alarm every week forever — and a permanently red safety
    net is worse than none, because it teaches operators to ignore the alert
    that is supposed to catch a genuinely corrupt backup.
    """
    from app.services import restore_service

    record = _record(
        encrypted=True, yd_path="backups/backup_20260915_215426.sql.gz.age"
    )
    session = _FakeSession(get_map={(restore_service.BackupHistory, 77): record})

    async def _unexpected(self, backup_id, workdir):
        raise AssertionError("materialize_dump must not run without the identity")

    monkeypatch.setattr(
        restore_service,
        "settings",
        _restore_settings(BACKUP_AGE_IDENTITY_FILE=str(tmp_path / "absent.key")),
    )
    monkeypatch.setattr(restore_service, "AsyncSessionLocal", _sticky_factory(session))
    monkeypatch.setattr(restore_service, "binary_available", lambda _b: True)
    monkeypatch.setattr(
        restore_service.RestoreService, "materialize_dump", _unexpected
    )

    report = await restore_service.RestoreService().verify_dump(77)

    assert report["skipped"] is True
    assert report["ok"] is False
    assert "identity" in report["reason"]
    assert record.verification_status == "no_identity"


@pytest.mark.asyncio
async def test_verify_dump_proceeds_when_encrypted_and_the_identity_is_present(
    monkeypatch, tmp_path
):
    """With the key mounted the check must run for real, not be skipped."""
    from app.services import restore_service

    identity = tmp_path / "age.key"
    identity.write_text("AGE-SECRET-KEY-1TESTONLY\n")

    record = _record(
        encrypted=True, yd_path="backups/backup_20260915_215426.sql.gz.age"
    )
    session = _FakeSession(get_map={(restore_service.BackupHistory, 77): record})
    captured: dict = {}

    async def _fake_materialize(self, backup_id, workdir):
        captured["materialized"] = backup_id
        path = Path(workdir) / "backup.dump"
        path.write_bytes(b"archive")
        return str(path)

    async def _fake_run_command(cmd, **kwargs):
        captured["cmd"] = cmd
        return "; comment\n1; 0 TABLE public users\n2; 0 TABLE DATA public users\n"

    monkeypatch.setattr(
        restore_service,
        "settings",
        _restore_settings(BACKUP_AGE_IDENTITY_FILE=str(identity)),
    )
    monkeypatch.setattr(restore_service, "AsyncSessionLocal", _sticky_factory(session))
    monkeypatch.setattr(restore_service, "binary_available", lambda _b: True)
    monkeypatch.setattr(
        restore_service.RestoreService, "materialize_dump", _fake_materialize
    )
    monkeypatch.setattr(restore_service, "run_command", _fake_run_command)

    report = await restore_service.RestoreService().verify_dump(77)

    assert captured["materialized"] == 77
    assert report.get("skipped") is not True
    assert report["ok"] is True
    assert record.verification_status == "ok"


def test_decryption_possible_tracks_the_identity_file(monkeypatch, tmp_path):
    from app.services import restore_service

    present = tmp_path / "age.key"
    present.write_text("AGE-SECRET-KEY-1TESTONLY\n")

    monkeypatch.setattr(
        restore_service,
        "settings",
        _restore_settings(BACKUP_AGE_IDENTITY_FILE=str(present)),
    )
    assert restore_service.RestoreService.decryption_possible(False) is True
    assert restore_service.RestoreService.decryption_possible(True) is True

    monkeypatch.setattr(
        restore_service,
        "settings",
        _restore_settings(BACKUP_AGE_IDENTITY_FILE=str(tmp_path / "absent.key")),
    )
    # A plain dump never needs a key; an encrypted one does.
    assert restore_service.RestoreService.decryption_possible(False) is True
    assert restore_service.RestoreService.decryption_possible(True) is False


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
async def test_restore_drill_skips_without_touching_the_cluster(monkeypatch, tmp_path):
    """An encrypted backup cannot be drilled while the key is off the host.

    The drill must report ``skipped`` / ``no_identity`` and must not create a
    throwaway database, and it must not push a failure into the drill metric:
    ``arv_backup_restore_drill_last_timestamp_seconds`` has to keep saying "no
    drill has proved this backup usable", not "the drill failed".
    """
    from app.services import restore_service

    record = _record(
        encrypted=True, yd_path="backups/backup_20260915_215426.sql.gz.age"
    )
    session = _FakeSession(get_map={(restore_service.BackupHistory, 77): record})
    metric_calls: list[bool] = []

    async def _unexpected(self, *args, **kwargs):
        raise AssertionError("the drill must not touch the cluster without the key")

    monkeypatch.setattr(
        restore_service,
        "settings",
        _restore_settings(BACKUP_AGE_IDENTITY_FILE=str(tmp_path / "absent.key")),
    )
    monkeypatch.setattr(restore_service, "AsyncSessionLocal", _sticky_factory(session))
    monkeypatch.setattr(
        restore_service.RestoreService, "materialize_dump", _unexpected
    )
    monkeypatch.setattr(
        restore_service.RestoreService, "_create_database", _unexpected
    )
    monkeypatch.setattr(
        restore_service, "record_restore_drill", lambda ok: metric_calls.append(ok)
    )

    report = await restore_service.RestoreService().restore_drill(77)

    assert report["skipped"] is True
    assert record.restore_test_status == "no_identity"
    assert metric_calls == [], "a skipped drill must not be recorded as a result"


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


# ----------------------------------------------------------------------
# Manual download (fetch_artifact)
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_artifact_returns_the_stored_db_artifact(monkeypatch):
    from app.services import restore_service
    from app.services.backup_service import BackupService

    async def _fake_download(self, backup_id, dest_path):
        Path(dest_path).write_bytes(b"encrypted-bytes")
        return dest_path

    session = _FakeSession(
        get_map={
            (restore_service.BackupHistory, 77): _record(
                encrypted=True, yd_path="backups/backup_20260915.sql.gz.age"
            )
        }
    )
    monkeypatch.setattr(restore_service, "settings", _restore_settings())
    monkeypatch.setattr(restore_service, "AsyncSessionLocal", _sticky_factory(session))
    monkeypatch.setattr(BackupService, "download_backup", _fake_download)

    workdir = tempfile.mkdtemp(prefix="arv-fetch-")
    try:
        info = await restore_service.RestoreService().fetch_artifact(77, workdir)

        assert info["filename"] == "backup_20260915.sql.gz.age"
        assert info["encrypted"] is True
        # The whole point of the manual path: what comes out is exactly what
        # was stored, so it stays useless to anyone without the key.
        assert info["plaintext"] is False
        assert Path(info["path"]).read_bytes() == b"encrypted-bytes"
        assert info["size_bytes"] == len(b"encrypted-bytes")
    finally:
        _rmtree(workdir)


@pytest.mark.asyncio
async def test_fetch_artifact_serves_a_local_secrets_archive(monkeypatch):
    """Secrets archives live in staging, not on Yandex Disk.

    ``yd_path`` carries an absolute local path for them, so the download path
    must copy from disk instead of asking the storage provider for a file that
    was never uploaded.
    """
    from app.services import restore_service
    from app.services.backup_service import BackupService

    staging = tempfile.mkdtemp(prefix="arv-staging-")
    archive = Path(staging) / "secrets_20260915_232500.tar.gz.age"
    archive.write_bytes(b"local-secrets")

    async def _unexpected(self, backup_id, dest_path):
        raise AssertionError("a local artifact must not be re-downloaded")

    session = _FakeSession(
        get_map={
            (restore_service.BackupHistory, 77): _record(
                encrypted=True, backup_type="secrets", yd_path=str(archive)
            )
        }
    )
    monkeypatch.setattr(restore_service, "settings", _restore_settings())
    monkeypatch.setattr(restore_service, "AsyncSessionLocal", _sticky_factory(session))
    monkeypatch.setattr(BackupService, "download_backup", _unexpected)

    workdir = tempfile.mkdtemp(prefix="arv-fetch-")
    try:
        info = await restore_service.RestoreService().fetch_artifact(77, workdir)

        assert info["filename"] == archive.name
        assert Path(info["path"]).read_bytes() == b"local-secrets"
        # It carries SECRET_KEY; it must not land world-readable in a temp dir.
        # Windows has no POSIX mode bits (chmod only toggles the read-only
        # flag), so this can only be asserted where the bits exist.
        if os.name == "posix":
            assert (os.stat(info["path"]).st_mode & 0o077) == 0
    finally:
        _rmtree(workdir)
        _rmtree(staging)


@pytest.mark.asyncio
async def test_fetch_artifact_refuses_media_snapshots(monkeypatch):
    from app.services import restore_service

    session = _FakeSession(
        get_map={(restore_service.BackupHistory, 77): _record(backup_type="media")}
    )
    monkeypatch.setattr(restore_service, "settings", _restore_settings())
    monkeypatch.setattr(restore_service, "AsyncSessionLocal", _sticky_factory(session))

    workdir = tempfile.mkdtemp(prefix="arv-fetch-")
    try:
        with pytest.raises(restore_service.ArtifactUnavailable) as excinfo:
            await restore_service.RestoreService().fetch_artifact(77, workdir)
        # The operator must be told what to do instead, not just "no".
        assert "restic" in str(excinfo.value)
    finally:
        _rmtree(workdir)


@pytest.mark.asyncio
async def test_fetch_artifact_decrypt_needs_the_identity(monkeypatch):
    from app.services import restore_service
    from app.services.backup_service import BackupService

    async def _fake_download(self, backup_id, dest_path):
        Path(dest_path).write_bytes(b"encrypted")
        return dest_path

    session = _FakeSession(
        get_map={(restore_service.BackupHistory, 77): _record(encrypted=True)}
    )
    monkeypatch.setattr(
        restore_service,
        "settings",
        _restore_settings(BACKUP_AGE_IDENTITY_FILE="/nonexistent/backup-age.key"),
    )
    monkeypatch.setattr(restore_service, "AsyncSessionLocal", _sticky_factory(session))
    monkeypatch.setattr(BackupService, "download_backup", _fake_download)

    workdir = tempfile.mkdtemp(prefix="arv-fetch-")
    try:
        with pytest.raises(restore_service.DecryptionUnavailable):
            await restore_service.RestoreService().fetch_artifact(
                77, workdir, decrypt=True
            )
    finally:
        _rmtree(workdir)


@pytest.mark.asyncio
async def test_fetch_artifact_decrypts_when_the_identity_is_present(monkeypatch, tmp_path):
    from app.services import restore_service
    from app.services.backup_service import BackupService

    identity = tmp_path / "backup-age.key"
    identity.write_text("AGE-SECRET-KEY-1...")

    async def _fake_download(self, backup_id, dest_path):
        Path(dest_path).write_bytes(b"ciphertext")
        return dest_path

    async def _fake_decrypt(self, src, dst):
        Path(dst).write_bytes(b"plaintext-dump")

    session = _FakeSession(
        get_map={
            (restore_service.BackupHistory, 77): _record(
                encrypted=True, yd_path="backups/b.sql.gz.age"
            )
        }
    )
    monkeypatch.setattr(
        restore_service,
        "settings",
        _restore_settings(BACKUP_AGE_IDENTITY_FILE=str(identity)),
    )
    monkeypatch.setattr(restore_service, "AsyncSessionLocal", _sticky_factory(session))
    monkeypatch.setattr(BackupService, "download_backup", _fake_download)
    monkeypatch.setattr(restore_service.RestoreService, "_decrypt_file", _fake_decrypt)

    workdir = tempfile.mkdtemp(prefix="arv-fetch-")
    try:
        info = await restore_service.RestoreService().fetch_artifact(
            77, workdir, decrypt=True
        )

        assert info["plaintext"] is True
        assert info["encrypted"] is True  # as stored, and reported as such
        assert info["filename"] == "b.sql.gz"
        assert Path(info["path"]).read_bytes() == b"plaintext-dump"
        # The ciphertext must not be left sitting beside the plaintext.
        assert not (Path(workdir) / "b.sql.gz.age").exists()
    finally:
        _rmtree(workdir)


@pytest.mark.asyncio
async def test_fetch_artifact_rejects_a_missing_backup(monkeypatch):
    from app.services import restore_service

    session = _FakeSession(get_map={})
    monkeypatch.setattr(restore_service, "settings", _restore_settings())
    monkeypatch.setattr(restore_service, "AsyncSessionLocal", _sticky_factory(session))

    workdir = tempfile.mkdtemp(prefix="arv-fetch-")
    try:
        with pytest.raises(RuntimeError, match="not found"):
            await restore_service.RestoreService().fetch_artifact(77, workdir)
    finally:
        _rmtree(workdir)


# ----------------------------------------------------------------------
# Target database creation (the step that used to be manual)
# ----------------------------------------------------------------------


def _stub_restore_pipeline(monkeypatch, restore_service, *, exists, count=15):
    """Wire a RestoreService whose DB calls are all recorded, not executed."""
    created: list[str] = []

    async def _fake_materialize(self, backup_id, workdir):
        path = Path(workdir) / "backup.dump"
        path.write_bytes(b"archive")
        return str(path)

    async def _exists(self, name):
        return exists

    async def _create(self, name):
        created.append(name)

    async def _restore_into(self, database, dump_path):
        return None

    async def _count(self, database):
        return count

    monkeypatch.setattr(restore_service, "settings", _restore_settings())
    monkeypatch.setattr(
        restore_service.RestoreService, "materialize_dump", _fake_materialize
    )
    monkeypatch.setattr(restore_service.RestoreService, "_database_exists", _exists)
    monkeypatch.setattr(restore_service.RestoreService, "_create_database", _create)
    monkeypatch.setattr(
        restore_service.RestoreService, "_pg_restore_into", _restore_into
    )
    monkeypatch.setattr(restore_service.RestoreService, "_count_tables", _count)
    return created


@pytest.mark.asyncio
async def test_restore_to_creates_the_target_database_when_asked(monkeypatch):
    from app.services import restore_service

    created = _stub_restore_pipeline(monkeypatch, restore_service, exists=False)

    report = await restore_service.RestoreService().restore_to(
        77, "vertex_ar_recovered", create_if_missing=True
    )

    assert report["ok"] is True
    assert report["created_database"] is True
    assert created == ["vertex_ar_recovered"]


@pytest.mark.asyncio
async def test_restore_to_does_not_create_a_database_by_default(monkeypatch):
    """Without --create-db the old behaviour stands: the operator owns the DB."""
    from app.services import restore_service

    created = _stub_restore_pipeline(monkeypatch, restore_service, exists=False)

    report = await restore_service.RestoreService().restore_to(77, "vertex_ar_recovered")

    assert report["ok"] is True
    assert report["created_database"] is False
    assert created == []


@pytest.mark.asyncio
async def test_restore_to_leaves_an_existing_database_alone(monkeypatch):
    """--create-db must be idempotent, not a way to clobber a database."""
    from app.services import restore_service

    created = _stub_restore_pipeline(monkeypatch, restore_service, exists=True)

    report = await restore_service.RestoreService().restore_to(
        77, "vertex_ar_recovered", create_if_missing=True
    )

    assert report["ok"] is True
    assert report["created_database"] is False
    assert created == []



# ----------------------------------------------------------------------
# restore_from_file: the only path that works when the database is gone
# ----------------------------------------------------------------------
#
# restore_to resolves its storage token from ``companies.yandex_disk_token``,
# i.e. from the database. That makes it useless in the scenario recovery exists
# for: the database is gone, so the token is gone, so the artifact cannot be
# fetched. restore_from_file takes the artifact as a file instead and never
# touches the database.


def _stub_cluster(monkeypatch, restore_service, *, exists=False, count=15):
    """Stub the cluster side, leaving materialisation real.

    The point of these tests is the decrypt/decompress path, so only the
    PostgreSQL calls are replaced. The dump is captured as *bytes*, not as a
    path: the work directory is removed in the service's ``finally`` block, so
    a recorded path would be gone by the time the test looks at it.
    """
    created: list[str] = []
    restored: list[bytes] = []

    async def _exists(self, name):
        return exists

    async def _create(self, name):
        created.append(name)

    async def _restore_into(self, database, dump_path):
        restored.append(Path(dump_path).read_bytes())

    async def _count(self, database):
        return count

    monkeypatch.setattr(restore_service.RestoreService, "_database_exists", _exists)
    monkeypatch.setattr(restore_service.RestoreService, "_create_database", _create)
    monkeypatch.setattr(
        restore_service.RestoreService, "_pg_restore_into", _restore_into
    )
    monkeypatch.setattr(restore_service.RestoreService, "_count_tables", _count)
    return created, restored


def _write_gz_artifact(path: Path, payload: bytes = b"PGDMP archive") -> None:
    with gzip.open(path, "wb") as handle:
        handle.write(payload)


@pytest.mark.asyncio
async def test_restore_from_file_needs_no_database(monkeypatch, tmp_path):
    """No session, no token, no database — that is the whole point."""
    from app.services import restore_service

    monkeypatch.setattr(restore_service, "settings", _restore_settings())

    def _no_session(*_args, **_kwargs):
        raise AssertionError("restore_from_file must not open a database session")

    monkeypatch.setattr(restore_service, "AsyncSessionLocal", _no_session)
    created, restored = _stub_cluster(monkeypatch, restore_service, exists=False)

    artifact = tmp_path / "backup_20260916_030000.sql.gz"
    _write_gz_artifact(artifact)

    report = await restore_service.RestoreService().restore_from_file(
        str(artifact), "vertex_ar_recovered", create_if_missing=True
    )

    assert report["ok"] is True
    assert report["tables_restored"] == 15
    assert report["created_database"] is True
    assert report["source_file"] == str(artifact)
    assert created == ["vertex_ar_recovered"]
    # what reached pg_restore is the decompressed payload, not the gzip
    assert restored == [b"PGDMP archive"]


@pytest.mark.asyncio
async def test_restore_from_file_decrypts_an_age_artifact(monkeypatch, tmp_path):
    """A .age artifact is opened, and the source directory is left untouched.

    The operator's copy may be the only one in existence and may sit in a
    directory we have no business writing to, so decrypted output must land in
    the work directory, never beside the source.
    """
    from app.services import restore_service

    decrypted: list[tuple[str, str]] = []

    async def _fake_decrypt(self, src, dst):
        decrypted.append((src, dst))
        _write_gz_artifact(Path(dst), b"PGDMP decrypted")

    monkeypatch.setattr(restore_service, "settings", _restore_settings())
    monkeypatch.setattr(
        restore_service.RestoreService, "_decrypt_file", _fake_decrypt
    )
    _, restored = _stub_cluster(monkeypatch, restore_service, exists=False)

    artifact = tmp_path / "backup_20260916_030000.sql.gz.age"
    artifact.write_bytes(b"age ciphertext")
    before = sorted(p.name for p in tmp_path.iterdir())

    report = await restore_service.RestoreService().restore_from_file(
        str(artifact), "vertex_ar_recovered", create_if_missing=True
    )

    assert report["ok"] is True
    assert decrypted and decrypted[0][0] == str(artifact)
    assert restored == [b"PGDMP decrypted"]
    # nothing was written next to the source
    assert sorted(p.name for p in tmp_path.iterdir()) == before


@pytest.mark.asyncio
async def test_restore_from_file_encrypted_override(monkeypatch, tmp_path):
    """A renamed encrypted artifact must be decryptable on request.

    Inference is by the .age suffix, so stripping the suffix would otherwise
    send ciphertext to gzip and fail with a confusing error.
    """
    from app.services import restore_service

    called: list[str] = []

    async def _fake_decrypt(self, src, dst):
        called.append(src)
        _write_gz_artifact(Path(dst), b"PGDMP decrypted")

    monkeypatch.setattr(restore_service, "settings", _restore_settings())
    monkeypatch.setattr(
        restore_service.RestoreService, "_decrypt_file", _fake_decrypt
    )
    _stub_cluster(monkeypatch, restore_service, exists=False)

    artifact = tmp_path / "renamed_artifact.sql.gz"
    artifact.write_bytes(b"age ciphertext")

    report = await restore_service.RestoreService().restore_from_file(
        str(artifact), "vertex_ar_recovered", create_if_missing=True, encrypted=True
    )

    assert report["ok"] is True
    assert called == [str(artifact)]


@pytest.mark.asyncio
async def test_restore_from_file_still_refuses_the_live_database(monkeypatch, tmp_path):
    """The live-database guard must hold on every restore entry point."""
    from app.services import restore_service

    monkeypatch.setattr(restore_service, "settings", _restore_settings())
    artifact = tmp_path / "backup.sql.gz"
    _write_gz_artifact(artifact)

    with pytest.raises(RuntimeError, match="Refusing to restore over the live database"):
        await restore_service.RestoreService().restore_from_file(
            str(artifact), "vertex_ar"
        )


@pytest.mark.asyncio
async def test_restore_from_file_rejects_unsafe_target_names(monkeypatch, tmp_path):
    from app.services import restore_service

    monkeypatch.setattr(restore_service, "settings", _restore_settings())
    artifact = tmp_path / "backup.sql.gz"
    _write_gz_artifact(artifact)

    with pytest.raises(ValueError, match="Unsafe target database name"):
        await restore_service.RestoreService().restore_from_file(
            str(artifact), 'vertex_ar"; DROP DATABASE vertex_ar; --'
        )


@pytest.mark.asyncio
async def test_restore_from_file_reports_a_missing_artifact(monkeypatch, tmp_path):
    """A typo in the path must be a clear failure, not a crash."""
    from app.services import restore_service

    monkeypatch.setattr(restore_service, "settings", _restore_settings())

    report = await restore_service.RestoreService().restore_from_file(
        str(tmp_path / "nope.sql.gz"), "vertex_ar_recovered"
    )

    assert report["ok"] is False
    assert "Artifact not found" in report["error"]


@pytest.mark.asyncio
async def test_restore_from_file_reports_an_empty_artifact(monkeypatch, tmp_path):
    """A truncated download is a real failure mode; say so plainly."""
    from app.services import restore_service

    monkeypatch.setattr(restore_service, "settings", _restore_settings())
    artifact = tmp_path / "backup.sql.gz"
    artifact.write_bytes(b"")

    report = await restore_service.RestoreService().restore_from_file(
        str(artifact), "vertex_ar_recovered"
    )

    assert report["ok"] is False
    assert "empty" in report["error"]


@pytest.mark.asyncio
async def test_restore_from_file_fails_loudly_without_the_age_identity(
    monkeypatch, tmp_path
):
    """Encrypted and no key must not look like success."""
    from app.services import restore_service

    monkeypatch.setattr(
        restore_service, "settings", _restore_settings(BACKUP_AGE_IDENTITY_FILE="")
    )
    artifact = tmp_path / "backup.sql.gz.age"
    artifact.write_bytes(b"age ciphertext")

    report = await restore_service.RestoreService().restore_from_file(
        str(artifact), "vertex_ar_recovered"
    )

    assert report["ok"] is False
    assert "BACKUP_AGE_IDENTITY_FILE" in report["error"]
