"""Tests for the backup CLI (``app/cli/backup.py``) and the host scripts.

The shell scripts in ``deploy/backup/`` are intentionally thin, but a syntax
error in one of them means the backup silently never runs — so they are parsed
by ``bash -n`` here.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.cli import backup as backup_cli
from app.utils.command import CommandError


def _cli_settings(**overrides) -> SimpleNamespace:
    base = {
        "BACKUP_STAGING_DIR": "/var/backups/arv",
        "BACKUP_AGE_RECIPIENT": "age1example",
        "BACKUP_AGE_BINARY": "age",
        "BACKUP_RCLONE_BINARY": "rclone",
        "BACKUP_SECONDARY_RCLONE_REMOTE": "",
        "BACKUP_MAX_AGE_HOURS": 26,
        "BACKUP_SECRETS_MAX_AGE_HOURS": 8 * 24,
        "encryption_enabled": True,
        "secondary_target_enabled": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


# ----------------------------------------------------------------------
# Argument parsing
# ----------------------------------------------------------------------


def test_parser_exposes_every_operational_command():
    parser = backup_cli.build_parser()

    for command in (
        "db", "media", "secrets", "verify", "verify-media", "drill",
        "restore", "status", "notify",
    ):
        args = parser.parse_args([command] if command != "restore" else ["restore", "1", "--target-db", "x"])
        assert callable(args.func)


def test_restore_requires_a_target_database():
    parser = backup_cli.build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["restore", "42"])


def test_default_trigger_is_scheduled():
    parser = backup_cli.build_parser()

    assert parser.parse_args(["db"]).trigger == "scheduled"
    assert parser.parse_args(["--trigger", "manual", "db"]).trigger == "manual"


# ----------------------------------------------------------------------
# Commands
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cmd_db_returns_zero_on_success(monkeypatch):
    record = SimpleNamespace(
        id=1, status="success", backup_type="db", target="primary",
        encrypted=True, size_bytes=10, duration_seconds=2,
        yd_path="daily/backup.sql.gz.age", error_message=None,
    )

    async def _fake_run_backup(self, **kwargs):
        return record

    monkeypatch.setattr(backup_cli.BackupService, "run_backup", _fake_run_backup)
    _patch_backup_settings(monkeypatch)

    args = backup_cli.build_parser().parse_args(["db", "--company-id", "5"])
    assert await backup_cli.cmd_db(args) == 0


@pytest.mark.asyncio
async def test_cmd_db_returns_one_on_failure(monkeypatch):
    record = SimpleNamespace(
        id=2, status="failed", backup_type="db", target="primary",
        encrypted=False, size_bytes=None, duration_seconds=1,
        yd_path=None, error_message="pg_dump exited with code 1",
    )

    async def _fake_run_backup(self, **kwargs):
        return record

    monkeypatch.setattr(backup_cli.BackupService, "run_backup", _fake_run_backup)
    _patch_backup_settings(monkeypatch)

    args = backup_cli.build_parser().parse_args(["db"])
    assert await backup_cli.cmd_db(args) == 1


@pytest.mark.asyncio
async def test_cmd_db_defaults_the_company_from_system_settings(monkeypatch):
    """``backup-db.sh`` has no way to pass --company-id.

    Without this fallback the whole ``arv-backup-db.timer`` path — the one the
    docs tell operators to install — dies with "Yandex Disk provider not
    available for company_id=None", because the dump is shipped through a
    company's Yandex Disk and the CLI defaulted the id to None.
    """
    captured: dict = {}

    async def _fake_run_backup(self, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            id=3, status="success", backup_type="db", target="primary",
            encrypted=True, size_bytes=1, duration_seconds=1,
            yd_path="daily/x.sql.gz.age", error_message=None,
        )

    monkeypatch.setattr(backup_cli.BackupService, "run_backup", _fake_run_backup)
    _patch_backup_settings(monkeypatch, company_id=4, yd_folder="backups")

    args = backup_cli.build_parser().parse_args(["db"])

    assert await backup_cli.cmd_db(args) == 0
    assert captured["company_id"] == 4
    assert captured["yd_folder"] == "backups"


@pytest.mark.asyncio
async def test_cmd_db_reports_a_missing_backup_company(monkeypatch):
    async def _fake_run_backup(self, **kwargs):
        raise AssertionError("must not attempt a backup without a company")

    monkeypatch.setattr(backup_cli.BackupService, "run_backup", _fake_run_backup)
    _patch_backup_settings(monkeypatch, company_id=None)

    args = backup_cli.build_parser().parse_args(["db"])

    assert await backup_cli.cmd_db(args) == 2


@pytest.mark.asyncio
async def test_cmd_media_reports_not_configured(monkeypatch):
    monkeypatch.setattr(
        backup_cli.MediaBackupService, "available", staticmethod(lambda: False)
    )

    args = backup_cli.build_parser().parse_args(["media"])
    assert await backup_cli.cmd_media(args) == 2


@pytest.mark.asyncio
async def test_cmd_media_returns_zero_on_success(monkeypatch):
    record = SimpleNamespace(
        id=3, status="success", backup_type="media", target="primary",
        encrypted=True, size_bytes=100, duration_seconds=5,
        yd_path=None, error_message=None,
    )

    async def _fake_run_backup(self, **kwargs):
        return record

    monkeypatch.setattr(
        backup_cli.MediaBackupService, "available", staticmethod(lambda: True)
    )
    monkeypatch.setattr(backup_cli.MediaBackupService, "run_backup", _fake_run_backup)

    args = backup_cli.build_parser().parse_args(["media"])
    assert await backup_cli.cmd_media(args) == 0


@pytest.mark.asyncio
async def test_cmd_verify_scopes_the_check_to_database_backups(monkeypatch):
    """Media and secrets rows must never reach the ``pg_restore`` checks.

    A media row has no ``yd_path`` and no ``checksum`` (restic manages its own
    integrity), so including it would report a spurious failure and turn the
    weekly verify timer permanently red.
    """
    captured: dict = {}

    class _Service:
        def __init__(self, *args, **kwargs):
            pass

        async def list_backups(self, session, **kwargs):
            captured.update(kwargs)
            return []

    monkeypatch.setattr(backup_cli, "BackupService", _Service)
    monkeypatch.setattr(backup_cli, "AsyncSessionLocal", _FakeSession)

    args = backup_cli.build_parser().parse_args(["verify", "--limit", "3"])

    assert await backup_cli.cmd_verify(args) == 1  # nothing to verify
    assert captured == {"limit": 3, "backup_type": "db"}


@pytest.mark.asyncio
async def test_cmd_verify_treats_a_skipped_toc_as_success(monkeypatch):
    """No key on the host is not a verification failure."""
    record = SimpleNamespace(
        id=139,
        backup_type="db",
        status="success",
        yd_path="backups/backup_20260915_215426.sql.gz.age",
        checksum="deadbeef",
    )

    class _Service:
        def __init__(self, *args, **kwargs):
            pass

        async def list_backups(self, session, **kwargs):
            return [record]

        async def verify_backup_integrity(self, backup_id):
            return True

    class _Restore:
        async def verify_dump(self, backup_id):
            return {"ok": False, "skipped": True, "reason": "no identity on host"}

    monkeypatch.setattr(backup_cli, "BackupService", _Service)
    monkeypatch.setattr(backup_cli, "RestoreService", _Restore)
    monkeypatch.setattr(backup_cli, "AsyncSessionLocal", _FakeSession)

    args = backup_cli.build_parser().parse_args(["verify"])

    assert await backup_cli.cmd_verify(args) == 0


@pytest.mark.asyncio
async def test_cmd_verify_still_fails_on_a_checksum_mismatch(monkeypatch):
    """Skipping the TOC must not mask a real checksum failure."""
    record = SimpleNamespace(
        id=139,
        backup_type="db",
        status="success",
        yd_path="backups/backup_20260915_215426.sql.gz.age",
        checksum="deadbeef",
    )

    class _Service:
        def __init__(self, *args, **kwargs):
            pass

        async def list_backups(self, session, **kwargs):
            return [record]

        async def verify_backup_integrity(self, backup_id):
            return False

    class _Restore:
        async def verify_dump(self, backup_id):
            return {"ok": False, "skipped": True, "reason": "no identity on host"}

    monkeypatch.setattr(backup_cli, "BackupService", _Service)
    monkeypatch.setattr(backup_cli, "RestoreService", _Restore)
    monkeypatch.setattr(backup_cli, "AsyncSessionLocal", _FakeSession)

    args = backup_cli.build_parser().parse_args(["verify"])

    assert await backup_cli.cmd_verify(args) == 1


@pytest.mark.asyncio
async def test_cmd_verify_skips_rows_that_never_uploaded_an_artifact(monkeypatch):
    """A failed run has nothing to checksum.

    Reporting it as a checksum failure would keep the weekly timer red long
    after the incident recovered. "The newest backup failed" is what `status`
    and the backup_age metric are for.
    """
    record = SimpleNamespace(
        id=142, backup_type="db", status="failed", yd_path=None, checksum=None
    )

    class _Service:
        def __init__(self, *args, **kwargs):
            pass

        async def list_backups(self, session, **kwargs):
            return [record]

        async def verify_backup_integrity(self, backup_id):
            raise AssertionError("nothing to verify on a row without an artifact")

    monkeypatch.setattr(backup_cli, "BackupService", _Service)
    monkeypatch.setattr(backup_cli, "AsyncSessionLocal", _FakeSession)

    args = backup_cli.build_parser().parse_args(["verify"])

    assert await backup_cli.cmd_verify(args) == 0


@pytest.mark.asyncio
async def test_cmd_verify_media_reports_not_configured(monkeypatch):
    monkeypatch.setattr(
        backup_cli.MediaBackupService, "available", staticmethod(lambda: False)
    )

    args = backup_cli.build_parser().parse_args(["verify-media"])

    assert await backup_cli.cmd_verify_media(args) == 2


@pytest.mark.asyncio
async def test_cmd_verify_media_passes_the_read_data_subset(monkeypatch):
    captured: dict = {}

    async def _check(self, read_data_subset="5%"):
        captured["subset"] = read_data_subset
        return False

    monkeypatch.setattr(
        backup_cli.MediaBackupService, "available", staticmethod(lambda: True)
    )
    monkeypatch.setattr(backup_cli.MediaBackupService, "check_integrity", _check)

    args = backup_cli.build_parser().parse_args(
        ["verify-media", "--read-data-subset", "2%"]
    )

    assert await backup_cli.cmd_verify_media(args) == 1
    assert captured["subset"] == "2%"


@pytest.mark.asyncio
async def test_cmd_verify_media_returns_zero_when_the_repository_is_healthy(
    monkeypatch,
):
    async def _check(self, read_data_subset="5%"):
        return True

    monkeypatch.setattr(
        backup_cli.MediaBackupService, "available", staticmethod(lambda: True)
    )
    monkeypatch.setattr(backup_cli.MediaBackupService, "check_integrity", _check)

    args = backup_cli.build_parser().parse_args(["verify-media"])

    assert await backup_cli.cmd_verify_media(args) == 0


@pytest.mark.asyncio
async def test_cmd_drill_treats_a_skipped_drill_as_success(monkeypatch):
    """A skipped drill must not trip OnFailure= on the monthly timer."""
    record = SimpleNamespace(id=139)

    class _Service:
        def __init__(self, *args, **kwargs):
            pass

        async def get_last_status(self, session, **kwargs):
            return record

    class _Restore:
        async def restore_drill(self, backup_id):
            return {"ok": False, "skipped": True, "reason": "no identity on host"}

    monkeypatch.setattr(backup_cli, "BackupService", _Service)
    monkeypatch.setattr(backup_cli, "RestoreService", _Restore)
    monkeypatch.setattr(backup_cli, "AsyncSessionLocal", _FakeSession)

    args = backup_cli.build_parser().parse_args(["drill"])

    assert await backup_cli.cmd_drill(args) == 0


@pytest.mark.asyncio
async def test_cmd_secrets_encrypts_and_removes_the_plaintext_archive(monkeypatch):
    workdir = Path(tempfile.mkdtemp(prefix="arv-secrets-"))
    secret_file = workdir / "app.env"
    secret_file.write_text("SECRET_KEY=super-secret\n")
    stage = workdir / "stage"

    captured: dict = {}

    async def _fake_run_command(cmd, **kwargs):
        captured["cmd"] = cmd
        # age --encrypt --recipient R --output <dst> <src>
        out_index = cmd.index("--output") + 1
        Path(cmd[out_index]).write_bytes(b"encrypted")
        return ""

    async def _fake_heartbeat(status="success", detail=""):
        captured["heartbeat"] = status
        return True

    monkeypatch.setattr(backup_cli, "settings", _cli_settings())
    monkeypatch.setattr(
        backup_cli, "SECRET_PATHS", ((str(secret_file), "app/.env", True, ()),)
    )
    monkeypatch.setattr(backup_cli, "run_command", _fake_run_command)
    monkeypatch.setattr(backup_cli, "send_heartbeat", _fake_heartbeat)
    _stub_secrets_history(monkeypatch)

    args = backup_cli.build_parser().parse_args(["secrets", "--stage", str(stage)])
    try:
        assert await backup_cli.cmd_secrets(args) == 0

        artifacts = list(stage.glob("secrets_*.tar.gz.age"))
        assert len(artifacts) == 1
        # The plaintext tar must not be left behind next to the ciphertext.
        assert list(stage.glob("secrets_*.tar.gz")) == []
        assert "--encrypt" in captured["cmd"]
        assert "age1example" in captured["cmd"]
        assert captured["heartbeat"] == "success"
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_cmd_secrets_warns_when_encryption_is_disabled(monkeypatch):
    workdir = Path(tempfile.mkdtemp(prefix="arv-secrets-plain-"))
    secret_file = workdir / "app.env"
    secret_file.write_text("SECRET_KEY=super-secret\n")
    stage = workdir / "stage"

    monkeypatch.setattr(
        backup_cli, "settings", _cli_settings(encryption_enabled=False)
    )
    monkeypatch.setattr(
        backup_cli, "SECRET_PATHS", ((str(secret_file), "app/.env", True, ()),)
    )
    monkeypatch.setattr(backup_cli, "send_heartbeat", _async_return(True))
    _stub_secrets_history(monkeypatch)

    args = backup_cli.build_parser().parse_args(["secrets", "--stage", str(stage)])
    try:
        assert await backup_cli.cmd_secrets(args) == 0
        assert len(list(stage.glob("secrets_*.tar.gz"))) == 1
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_cmd_secrets_pushes_to_the_secondary_remote(monkeypatch):
    workdir = Path(tempfile.mkdtemp(prefix="arv-secrets-rclone-"))
    secret_file = workdir / "app.env"
    secret_file.write_text("SECRET_KEY=super-secret\n")
    stage = workdir / "stage"

    calls: list[list[str]] = []

    async def _fake_run_command(cmd, **kwargs):
        calls.append(cmd)
        if cmd[1] == "--encrypt":
            Path(cmd[cmd.index("--output") + 1]).write_bytes(b"encrypted")
        return ""

    monkeypatch.setattr(
        backup_cli,
        "settings",
        _cli_settings(
            secondary_target_enabled=True,
            BACKUP_SECONDARY_RCLONE_REMOTE="s3secondary:arv-backups",
        ),
    )
    monkeypatch.setattr(backup_cli, "SECRET_PATHS", ((str(secret_file), "app/.env", True, ()),))
    monkeypatch.setattr(backup_cli, "run_command", _fake_run_command)
    monkeypatch.setattr(backup_cli, "send_heartbeat", _async_return(True))
    _stub_secrets_history(monkeypatch)

    args = backup_cli.build_parser().parse_args(["secrets", "--stage", str(stage)])
    try:
        assert await backup_cli.cmd_secrets(args) == 0
        rclone_calls = [cmd for cmd in calls if cmd[0] == "rclone"]
        assert len(rclone_calls) == 1
        # [rclone, copyto, <local artifact>, <remote destination>]
        assert rclone_calls[0][3].startswith("s3secondary:arv-backups/secrets/")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_cmd_secrets_creates_the_archive_unreadable_by_others(monkeypatch):
    """The archive holds SECRET_KEY; it must never be world-readable.

    ``tarfile.open(path, ...)`` applies the process umask, so the file used to
    appear as 0644 and stayed that way for the whole run — and permanently, if
    the run died before the ``chmod`` at the end.
    """
    workdir = Path(tempfile.mkdtemp(prefix="arv-secrets-mode-"))
    secret_file = workdir / "app.env"
    secret_file.write_text("SECRET_KEY=super-secret\n")
    stage = workdir / "stage"

    modes: list[int] = []
    real_open = os.open

    def _spy_open(path, flags, mode=0o777):
        modes.append(mode)
        return real_open(path, flags, mode)

    async def _fake_run_command(cmd, **kwargs):
        Path(cmd[cmd.index("--output") + 1]).write_bytes(b"encrypted")
        return ""

    monkeypatch.setattr(backup_cli, "settings", _cli_settings())
    monkeypatch.setattr(
        backup_cli, "SECRET_PATHS", ((str(secret_file), "app/.env", True, ()),)
    )
    monkeypatch.setattr(backup_cli, "run_command", _fake_run_command)
    monkeypatch.setattr(backup_cli, "send_heartbeat", _async_return(True))
    monkeypatch.setattr(backup_cli.os, "open", _spy_open)

    args = backup_cli.build_parser().parse_args(["secrets", "--stage", str(stage)])
    try:
        assert await backup_cli.cmd_secrets(args) == 0
        assert modes == [0o600], [oct(m) for m in modes]
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_cmd_secrets_never_leaves_a_plaintext_archive_behind(monkeypatch):
    """A failure before encryption used to leave a readable .env on disk.

    The old code removed the plaintext tar only inside the encryption success
    branch, so an exception raised earlier (an unreadable tree, a missing
    binary) left the archive in place — world-readable, because it was created
    with the default umask.
    """
    workdir = Path(tempfile.mkdtemp(prefix="arv-secrets-fail-"))
    secret_file = workdir / "app.env"
    secret_file.write_text("SECRET_KEY=super-secret\n")
    stage = workdir / "stage"

    async def _boom(cmd, **kwargs):
        raise CommandError("age: command not found")

    monkeypatch.setattr(backup_cli, "settings", _cli_settings())
    monkeypatch.setattr(
        backup_cli, "SECRET_PATHS", ((str(secret_file), "app/.env", True, ()),)
    )
    monkeypatch.setattr(backup_cli, "run_command", _boom)
    monkeypatch.setattr(backup_cli, "send_heartbeat", _async_return(True))
    _stub_secrets_history(monkeypatch)

    args = backup_cli.build_parser().parse_args(["secrets", "--stage", str(stage)])
    try:
        with pytest.raises(CommandError):
            await backup_cli.cmd_secrets(args)
        assert list(stage.glob("secrets_*")) == []
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_cmd_secrets_fails_when_a_required_path_is_missing(monkeypatch):
    """An archive without .env looks like a backup but is not one."""
    workdir = Path(tempfile.mkdtemp(prefix="arv-secrets-missing-"))
    stage = workdir / "stage"

    monkeypatch.setattr(backup_cli, "settings", _cli_settings())
    monkeypatch.setattr(
        backup_cli,
        "SECRET_PATHS",
        ((str(workdir / "absent.env"), "app/.env", True, ()),),
    )
    monkeypatch.setattr(backup_cli, "send_heartbeat", _async_return(True))
    _stub_secrets_history(monkeypatch)

    args = backup_cli.build_parser().parse_args(["secrets", "--stage", str(stage)])
    try:
        with pytest.raises(RuntimeError, match="required secret paths are missing"):
            await backup_cli.cmd_secrets(args)
        assert list(stage.glob("secrets_*")) == []
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_cmd_secrets_survives_an_unreadable_optional_path(monkeypatch):
    """A root-only tree must not take the whole archive down.

    /etc/letsencrypt/live and /archive are mode 0700 root, so a unit running as
    ``arv`` cannot descend into them. Letting that raise made the secrets
    backup impossible to run at all: it failed every week and alerted every
    week.
    """
    workdir = Path(tempfile.mkdtemp(prefix="arv-secrets-unreadable-"))
    secret_file = workdir / "app.env"
    secret_file.write_text("SECRET_KEY=super-secret\n")
    stage = workdir / "stage"
    locked = workdir / "root-only"
    locked.mkdir()

    added: list[str] = []

    class _FakeArchive:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def add(self, path, arcname=None):
            if path == str(locked):
                raise PermissionError(13, "Permission denied", str(path))
            added.append(arcname)

    def _fake_open(fileobj=None, mode=None, **kwargs):
        return _FakeArchive()

    async def _fake_run_command(cmd, **kwargs):
        Path(cmd[cmd.index("--output") + 1]).write_bytes(b"encrypted")
        return ""

    monkeypatch.setattr(backup_cli, "settings", _cli_settings())
    monkeypatch.setattr(
        backup_cli,
        "SECRET_PATHS",
        (
            (str(secret_file), "app/.env", True, ()),
            (str(locked), "etc/letsencrypt", False, ()),
        ),
    )
    monkeypatch.setattr(backup_cli.tarfile, "open", _fake_open)
    monkeypatch.setattr(backup_cli, "run_command", _fake_run_command)
    monkeypatch.setattr(backup_cli, "send_heartbeat", _async_return(True))
    _stub_secrets_history(monkeypatch)

    args = backup_cli.build_parser().parse_args(["secrets", "--stage", str(stage)])
    try:
        assert await backup_cli.cmd_secrets(args) == 0
        assert "app/.env" in added
        assert "etc/letsencrypt" not in added
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_cmd_notify_alerts_admins_and_trips_the_heartbeat(monkeypatch):
    captured: dict = {}

    async def _fake_send_critical_alerts(alerts, metrics):
        captured["alerts"] = alerts
        captured["metrics"] = metrics

    async def _fake_heartbeat(status="success", detail=""):
        captured["heartbeat"] = status
        return True

    # NOTE: patch through sys.modules. `app.services.__init__` rebinds the
    # package attribute `alert_service` to an AlertService *instance*, which
    # shadows the submodule for dotted attribute access (monkeypatch's string
    # form included) but not for `from ... import ...` inside the command.
    monkeypatch.setattr(
        sys.modules["app.services.alert_service"],
        "send_critical_alerts",
        _fake_send_critical_alerts,
    )
    monkeypatch.setattr(backup_cli, "send_heartbeat", _fake_heartbeat)

    args = backup_cli.build_parser().parse_args(
        ["notify", "--unit", "arv-backup-db.service", "--detail", "exit 1"]
    )
    assert await backup_cli.cmd_notify(args) == 0

    assert captured["alerts"][0].severity == "critical"
    assert "arv-backup-db.service" in captured["alerts"][0].message
    assert captured["heartbeat"] == "fail"


@pytest.mark.asyncio
async def test_cmd_restore_requires_target_db_and_delegates(monkeypatch):
    captured: dict = {}

    async def _fake_restore_to(self, backup_id, target_db, *, create_if_missing=False):
        captured["backup_id"] = backup_id
        captured["target_db"] = target_db
        captured["create_if_missing"] = create_if_missing
        return {
            "ok": True,
            "tables_restored": 15,
            "target_database": target_db,
            "created_database": create_if_missing,
            "duration_seconds": 1,
        }

    monkeypatch.setattr(backup_cli.RestoreService, "restore_to", _fake_restore_to)

    args = backup_cli.build_parser().parse_args(
        ["restore", "42", "--target-db", "vertex_ar_recovered"]
    )
    assert await backup_cli.cmd_restore(args) == 0
    assert captured == {
        "backup_id": 42,
        "target_db": "vertex_ar_recovered",
        # Opt-in: without the flag the operator still owns database creation.
        "create_if_missing": False,
    }


@pytest.mark.asyncio
async def test_cmd_restore_passes_create_db_through(monkeypatch):
    captured: dict = {}

    async def _fake_restore_to(self, backup_id, target_db, *, create_if_missing=False):
        captured["create_if_missing"] = create_if_missing
        return {
            "ok": True,
            "tables_restored": 15,
            "target_database": target_db,
            "created_database": True,
            "duration_seconds": 1,
        }

    monkeypatch.setattr(backup_cli.RestoreService, "restore_to", _fake_restore_to)

    args = backup_cli.build_parser().parse_args(
        ["restore", "42", "--target-db", "vertex_ar_recovered", "--create-db"]
    )
    assert await backup_cli.cmd_restore(args) == 0
    assert captured["create_if_missing"] is True


@pytest.mark.asyncio
async def test_cmd_restore_fails_loudly(monkeypatch):
    async def _fake_restore_to(self, backup_id, target_db, *, create_if_missing=False):
        return {"ok": False, "error": "permission denied", "target_database": target_db}

    monkeypatch.setattr(backup_cli.RestoreService, "restore_to", _fake_restore_to)

    args = backup_cli.build_parser().parse_args(
        ["restore", "42", "--target-db", "vertex_ar_recovered"]
    )
    assert await backup_cli.cmd_restore(args) == 1


# ----------------------------------------------------------------------
# restore --from-file: the path that works when the database is gone
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cmd_restore_from_file_does_not_need_a_backup_id(monkeypatch):
    """The whole point: no id, because the history table is unreachable."""
    captured: dict = {}

    async def _fake_from_file(
        self, artifact_path, target_db, *, create_if_missing=False, encrypted=None
    ):
        captured["artifact_path"] = artifact_path
        captured["target_db"] = target_db
        captured["create_if_missing"] = create_if_missing
        captured["encrypted"] = encrypted
        return {
            "ok": True,
            "tables_restored": 15,
            "target_database": target_db,
            "created_database": create_if_missing,
            "duration_seconds": 2,
            "source_file": artifact_path,
        }

    def _must_not_be_used(*_args, **_kwargs):
        raise AssertionError("restore_to must not run for --from-file")

    monkeypatch.setattr(
        backup_cli.RestoreService, "restore_from_file", _fake_from_file
    )
    monkeypatch.setattr(backup_cli.RestoreService, "restore_to", _must_not_be_used)

    args = backup_cli.build_parser().parse_args(
        [
            "restore",
            "--from-file",
            "/var/backups/arv/backup_20260916_030000.sql.gz.age",
            "--target-db",
            "vertex_ar_recovered",
            "--create-db",
        ]
    )
    assert await backup_cli.cmd_restore(args) == 0
    assert captured == {
        "artifact_path": "/var/backups/arv/backup_20260916_030000.sql.gz.age",
        "target_db": "vertex_ar_recovered",
        "create_if_missing": True,
        # Inference is by suffix, so no override unless asked for.
        "encrypted": None,
    }


@pytest.mark.asyncio
async def test_cmd_restore_from_file_passes_encrypted_override(monkeypatch):
    captured: dict = {}

    async def _fake_from_file(
        self, artifact_path, target_db, *, create_if_missing=False, encrypted=None
    ):
        captured["encrypted"] = encrypted
        return {
            "ok": True,
            "tables_restored": 1,
            "target_database": target_db,
            "created_database": False,
            "duration_seconds": 1,
            "source_file": artifact_path,
        }

    monkeypatch.setattr(
        backup_cli.RestoreService, "restore_from_file", _fake_from_file
    )

    args = backup_cli.build_parser().parse_args(
        [
            "restore",
            "--from-file",
            "/tmp/renamed.sql.gz",
            "--encrypted",
            "--target-db",
            "vertex_ar_recovered",
        ]
    )
    assert await backup_cli.cmd_restore(args) == 0
    assert captured["encrypted"] is True


@pytest.mark.asyncio
async def test_cmd_restore_rejects_both_id_and_from_file(monkeypatch):
    """Two sources would silently mean one of them is ignored."""
    args = backup_cli.build_parser().parse_args(
        [
            "restore",
            "42",
            "--from-file",
            "/tmp/backup.sql.gz",
            "--target-db",
            "vertex_ar_recovered",
        ]
    )
    assert await backup_cli.cmd_restore(args) == 2


@pytest.mark.asyncio
async def test_cmd_restore_requires_a_source(monkeypatch):
    args = backup_cli.build_parser().parse_args(
        ["restore", "--target-db", "vertex_ar_recovered"]
    )
    assert await backup_cli.cmd_restore(args) == 2


@pytest.mark.asyncio
async def test_cmd_restore_from_file_fails_loudly(monkeypatch):
    async def _fake_from_file(
        self, artifact_path, target_db, *, create_if_missing=False, encrypted=None
    ):
        return {
            "ok": False,
            "error": "Artifact not found: /tmp/nope.sql.gz",
            "target_database": target_db,
            "source_file": artifact_path,
        }

    monkeypatch.setattr(
        backup_cli.RestoreService, "restore_from_file", _fake_from_file
    )

    args = backup_cli.build_parser().parse_args(
        [
            "restore",
            "--from-file",
            "/tmp/nope.sql.gz",
            "--target-db",
            "vertex_ar_recovered",
        ]
    )
    assert await backup_cli.cmd_restore(args) == 1


# ----------------------------------------------------------------------
# download
# ----------------------------------------------------------------------


def _fetch_result(workdir: Path, name: str, payload: bytes, **overrides):
    path = workdir / name
    path.write_bytes(payload)
    info = {
        "path": str(path),
        "filename": name,
        "encrypted": True,
        "plaintext": False,
        "size_bytes": len(payload),
        "backup_type": "db",
    }
    info.update(overrides)
    return info


@pytest.mark.asyncio
async def test_cmd_download_writes_the_artifact_to_a_file(monkeypatch, tmp_path):
    async def _fake_fetch(self, backup_id, workdir, *, decrypt=False):
        return _fetch_result(Path(workdir), "backup_20260915.sql.gz.age", b"cipher")

    monkeypatch.setattr(backup_cli.RestoreService, "fetch_artifact", _fake_fetch)

    out = tmp_path / "pulled.age"
    args = backup_cli.build_parser().parse_args(["download", "42", "--output", str(out)])

    assert await backup_cli.cmd_download(args) == 0
    assert out.read_bytes() == b"cipher"


@pytest.mark.asyncio
async def test_cmd_download_treats_the_output_as_a_directory(monkeypatch, tmp_path):
    async def _fake_fetch(self, backup_id, workdir, *, decrypt=False):
        return _fetch_result(Path(workdir), "b.sql.gz.age", b"x")

    monkeypatch.setattr(backup_cli.RestoreService, "fetch_artifact", _fake_fetch)

    args = backup_cli.build_parser().parse_args(
        ["download", "42", "--output", str(tmp_path)]
    )

    assert await backup_cli.cmd_download(args) == 0
    assert (tmp_path / "b.sql.gz.age").read_bytes() == b"x"


@pytest.mark.asyncio
async def test_cmd_download_passes_decrypt_through(monkeypatch, tmp_path):
    seen: dict = {}

    async def _fake_fetch(self, backup_id, workdir, *, decrypt=False):
        seen["decrypt"] = decrypt
        return _fetch_result(Path(workdir), "b.sql.gz", b"plain", plaintext=True)

    monkeypatch.setattr(backup_cli.RestoreService, "fetch_artifact", _fake_fetch)

    args = backup_cli.build_parser().parse_args(
        ["download", "42", "--output", str(tmp_path), "--decrypt"]
    )

    assert await backup_cli.cmd_download(args) == 0
    assert seen["decrypt"] is True


@pytest.mark.asyncio
async def test_cmd_download_reports_media_as_unavailable(monkeypatch):
    from app.services import restore_service

    async def _boom(self, backup_id, workdir, *, decrypt=False):
        raise restore_service.ArtifactUnavailable("Media backups are restic snapshots")

    monkeypatch.setattr(backup_cli.RestoreService, "fetch_artifact", _boom)

    args = backup_cli.build_parser().parse_args(["download", "42"])
    # 2 = "understood, but not applicable" — not a crash.
    assert await backup_cli.cmd_download(args) == 2


@pytest.mark.asyncio
async def test_cmd_download_reports_a_missing_identity(monkeypatch):
    from app.services import restore_service

    async def _boom(self, backup_id, workdir, *, decrypt=False):
        raise restore_service.DecryptionUnavailable("no identity on this host")

    monkeypatch.setattr(backup_cli.RestoreService, "fetch_artifact", _boom)

    args = backup_cli.build_parser().parse_args(["download", "42", "--decrypt"])
    assert await backup_cli.cmd_download(args) == 2


@pytest.mark.asyncio
async def test_cmd_status_flags_a_stale_or_failed_backup(monkeypatch):
    from datetime import timedelta

    stale = SimpleNamespace(
        status="success",
        started_at=backup_cli.datetime.now(backup_cli.UTC).replace(tzinfo=None)
        - timedelta(hours=48),
        finished_at=backup_cli.datetime.now(backup_cli.UTC).replace(tzinfo=None)
        - timedelta(hours=48),
        verified_at=None,
        verification_status=None,
        restore_tested_at=None,
        restore_test_status=None,
    )

    async def _fake_get_last_status(self, session, backup_type=None):
        return stale if backup_type == "db" else None

    monkeypatch.setattr(
        backup_cli.BackupService, "get_last_status", _fake_get_last_status
    )
    monkeypatch.setattr(backup_cli, "settings", _cli_settings())
    monkeypatch.setattr(backup_cli, "AsyncSessionLocal", _sticky_session())

    args = backup_cli.build_parser().parse_args(["status"])
    # Stale db run plus "never run" for media/secrets.
    assert await backup_cli.cmd_status(args) == 1


@pytest.mark.asyncio
async def test_cmd_secrets_records_its_outcome_in_backup_history(monkeypatch):
    """Without a row the A3 job is invisible.

    ``backup status`` reported "secrets: never run" forever, so nothing could
    alert when the job silently stopped running — the same blind spot the db and
    media jobs already avoid.
    """
    workdir = Path(tempfile.mkdtemp(prefix="arv-secrets-record-"))
    secret_file = workdir / "app.env"
    secret_file.write_text("SECRET_KEY=super-secret\n")
    stage = workdir / "stage"

    captured: dict = {}

    async def _start(trigger):
        captured["trigger"] = trigger
        return 4242

    async def _finish(record_id, **kwargs):
        captured["record_id"] = record_id
        captured.update(kwargs)

    async def _fake_run_command(cmd, **kwargs):
        Path(cmd[cmd.index("--output") + 1]).write_bytes(b"encrypted")
        return ""

    monkeypatch.setattr(backup_cli, "settings", _cli_settings())
    monkeypatch.setattr(
        backup_cli, "SECRET_PATHS", ((str(secret_file), "app/.env", True, ()),)
    )
    monkeypatch.setattr(backup_cli, "_start_secrets_record", _start)
    monkeypatch.setattr(backup_cli, "_finish_secrets_record", _finish)
    monkeypatch.setattr(backup_cli, "run_command", _fake_run_command)
    monkeypatch.setattr(backup_cli, "send_heartbeat", _async_return(True))

    args = backup_cli.build_parser().parse_args(["secrets", "--stage", str(stage)])
    try:
        assert await backup_cli.cmd_secrets(args) == 0
        assert captured["record_id"] == 4242
        assert captured["trigger"] == "scheduled"
        assert captured["status"] == "success"
        assert captured["size_bytes"] > 0
        assert captured["checksum"]
        assert captured["artifact"].endswith(".age")
        assert captured.get("error_message") is None
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_cmd_secrets_records_a_failed_run(monkeypatch):
    workdir = Path(tempfile.mkdtemp(prefix="arv-secrets-record-fail-"))
    secret_file = workdir / "app.env"
    secret_file.write_text("SECRET_KEY=super-secret\n")
    stage = workdir / "stage"

    captured: dict = {}

    async def _start(trigger):
        return 4243

    async def _finish(record_id, **kwargs):
        captured.update(kwargs)

    async def _boom(cmd, **kwargs):
        raise CommandError("age: command not found")

    monkeypatch.setattr(backup_cli, "settings", _cli_settings())
    monkeypatch.setattr(
        backup_cli, "SECRET_PATHS", ((str(secret_file), "app/.env", True, ()),)
    )
    monkeypatch.setattr(backup_cli, "_start_secrets_record", _start)
    monkeypatch.setattr(backup_cli, "_finish_secrets_record", _finish)
    monkeypatch.setattr(backup_cli, "run_command", _boom)
    monkeypatch.setattr(backup_cli, "send_heartbeat", _async_return(True))

    args = backup_cli.build_parser().parse_args(["secrets", "--stage", str(stage)])
    try:
        with pytest.raises(CommandError):
            await backup_cli.cmd_secrets(args)
        assert captured["status"] == "failed"
        assert "age" in captured["error_message"]
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_cmd_status_applies_a_weekly_limit_to_the_secrets_archive(monkeypatch):
    """A weekly job must not be judged by the daily limit.

    With the daily rule a healthy secrets archive is reported stale six days out
    of seven — a false alarm that trains operators to ignore `status`.
    """
    from datetime import timedelta

    now = backup_cli.datetime.now(backup_cli.UTC).replace(tzinfo=None)
    recent = SimpleNamespace(
        status="success",
        started_at=now - timedelta(hours=2),
        finished_at=now - timedelta(hours=2),
        verified_at=None,
        verification_status=None,
        restore_tested_at=None,
        restore_test_status=None,
    )
    secrets = SimpleNamespace(
        status="success",
        started_at=now - timedelta(days=5),
        finished_at=now - timedelta(days=5),
        verified_at=None,
        verification_status=None,
        restore_tested_at=None,
        restore_test_status=None,
    )

    async def _fake_get_last_status(self, session, backup_type=None):
        return secrets if backup_type == "secrets" else recent

    monkeypatch.setattr(
        backup_cli.BackupService, "get_last_status", _fake_get_last_status
    )
    monkeypatch.setattr(backup_cli, "settings", _cli_settings())
    monkeypatch.setattr(backup_cli, "AsyncSessionLocal", _sticky_session())

    args = backup_cli.build_parser().parse_args(["status"])
    # 5 days: fine for a weekly archive.
    assert await backup_cli.cmd_status(args) == 0

    # 9 days: overdue even for a weekly job.
    secrets.started_at = secrets.finished_at = now - timedelta(days=9)
    assert await backup_cli.cmd_status(args) == 1


@pytest.mark.asyncio
async def test_cmd_secrets_succeeds_even_when_history_bookkeeping_fails(monkeypatch):
    """The archive on disk is what matters; the row is only how we learn about it.

    Exercising the real helpers (no stub) is also what proves the suite cannot
    reach a live database through them: on the server, an unstubbed run wrote
    junk rows into the production backup history.
    """
    workdir = Path(tempfile.mkdtemp(prefix="arv-secrets-nodb-"))
    secret_file = workdir / "app.env"
    secret_file.write_text("SECRET_KEY=super-secret\n")
    stage = workdir / "stage"

    class _BoomSession:
        async def __aenter__(self):
            raise RuntimeError("database is down")

        async def __aexit__(self, *exc):
            return False

    async def _fake_run_command(cmd, **kwargs):
        Path(cmd[cmd.index("--output") + 1]).write_bytes(b"encrypted")
        return ""

    monkeypatch.setattr(backup_cli, "settings", _cli_settings())
    monkeypatch.setattr(
        backup_cli, "SECRET_PATHS", ((str(secret_file), "app/.env", True, ()),)
    )
    monkeypatch.setattr(backup_cli, "run_command", _fake_run_command)
    monkeypatch.setattr(backup_cli, "send_heartbeat", _async_return(True))
    monkeypatch.setattr(backup_cli, "AsyncSessionLocal", lambda: _BoomSession())

    args = backup_cli.build_parser().parse_args(["secrets", "--stage", str(stage)])
    try:
        assert await backup_cli.cmd_secrets(args) == 0
        assert len(list(stage.glob("secrets_*.tar.gz.age"))) == 1
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def test_main_returns_nonzero_when_a_command_raises(monkeypatch):
    async def _boom(args):
        raise backup_cli.CommandError("pg_dump exited with code 1")

    monkeypatch.setattr(backup_cli, "cmd_db", _boom)
    parser = backup_cli.build_parser()
    args = parser.parse_args(["db"])
    monkeypatch.setattr(parser, "parse_args", lambda argv=None: args)
    monkeypatch.setattr(backup_cli, "build_parser", lambda: parser)

    assert backup_cli.main(["db"]) == 1


# ----------------------------------------------------------------------
# Host scripts
# ----------------------------------------------------------------------


def test_shell_scripts_are_syntactically_valid():
    bash = shutil.which("bash")
    if bash is None:  # pragma: no cover - Windows without Git Bash
        pytest.skip("bash is not available")

    script_dir = Path(__file__).resolve().parent.parent / "deploy" / "backup"
    scripts = sorted(script_dir.glob("*.sh"))
    assert scripts, "expected backup scripts to exist"

    for script in scripts:
        result = subprocess.run(
            [bash, "-n", str(script)], capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, f"{script.name}: {result.stderr}"


def test_every_backup_script_sources_the_shared_helper():
    script_dir = Path(__file__).resolve().parent.parent / "deploy" / "backup"

    for script in sorted(script_dir.glob("*.sh")):
        if script.name == "common.sh":
            continue
        assert "common.sh" in script.read_text(), f"{script.name} does not source common.sh"


def test_systemd_units_cover_every_backup_script():
    deploy = Path(__file__).resolve().parent.parent / "deploy"
    units = {path.name for path in (deploy / "systemd").glob("arv-backup-*")}

    for name in (
        "arv-backup-db.service", "arv-backup-db.timer",
        "arv-backup-media.service", "arv-backup-media.timer",
        "arv-backup-secrets.service", "arv-backup-secrets.timer",
        "arv-backup-verify.service", "arv-backup-verify.timer",
        "arv-backup-drill.service", "arv-backup-drill.timer",
        "arv-backup-alert@.service",
    ):
        assert name in units, f"missing systemd unit: {name}"


def test_every_timer_is_persistent_so_missed_runs_are_caught_up():
    deploy = Path(__file__).resolve().parent.parent / "deploy"

    timers = sorted((deploy / "systemd").glob("arv-backup-*.timer"))
    assert timers

    for timer in timers:
        text = timer.read_text()
        assert "Persistent=true" in text, f"{timer.name} would silently skip runs"


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


class _FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _sticky_session():
    return _FakeSession


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner


def _stub_secrets_history(monkeypatch):
    """Keep ``cmd_secrets`` off the database in tests.

    The command records a ``backup_history`` row. Left unstubbed, these tests
    write to whatever ``DATABASE_URL`` points at — which on the server is the
    production database. A bare ``pytest`` run did exactly that and inserted
    junk rows into the live backup history, one of them a ``failed`` row that
    then made ``backup status`` report the secrets archive as broken.
    """

    async def _start(trigger):
        return None

    async def _finish(record_id, **kwargs):
        return None

    monkeypatch.setattr(backup_cli, "_start_secrets_record", _start)
    monkeypatch.setattr(backup_cli, "_finish_secrets_record", _finish)


def _patch_backup_settings(monkeypatch, company_id=4, yd_folder="backups"):
    """Make ``cmd_db`` resolve its recipient company without touching a database.

    The service is imported lazily inside ``cmd_db``, so it has to be patched on
    the module that defines it rather than on ``backup_cli``.
    """
    from app.services.settings_service import SettingsService

    backup = SimpleNamespace(
        backup_company_id=company_id,
        backup_yd_folder=yd_folder,
        backup_enabled=True,
    )

    async def _get_all_settings(self):
        return SimpleNamespace(backup=backup)

    monkeypatch.setattr(SettingsService, "get_all_settings", _get_all_settings)
    monkeypatch.setattr(backup_cli, "AsyncSessionLocal", _FakeSession)


# ----------------------------------------------------------------------
# verify / drill --from-file: prove a backup usable without the database
# ----------------------------------------------------------------------
#
# The automated verify and drill cannot open an encrypted artifact — the age
# identity is kept off the production host by design — so the strongest
# automatic proof is a checksum. These commands let the operator take the
# artifact to wherever the key is and finish the job.


@pytest.mark.asyncio
async def test_cmd_verify_from_file_needs_no_session(monkeypatch):
    captured: dict = {}

    async def _fake_verify_file(
        self, artifact_path, *, encrypted=None, record_as=None
    ):
        captured["artifact_path"] = artifact_path
        captured["encrypted"] = encrypted
        captured["record_as"] = record_as
        return {"ok": True, "entries": 12, "tables": 9, "source_file": artifact_path}

    monkeypatch.setattr(backup_cli.RestoreService, "verify_file", _fake_verify_file)

    args = backup_cli.build_parser().parse_args(
        ["verify", "--from-file", "/tmp/backup.sql.gz.age"]
    )
    assert await backup_cli.cmd_verify(args) == 0
    assert captured == {
        "artifact_path": "/tmp/backup.sql.gz.age",
        "encrypted": None,
        "record_as": None,
    }


@pytest.mark.asyncio
async def test_cmd_verify_from_file_passes_record_as(monkeypatch):
    """--record-as is how a manual verify reaches the dashboard."""
    captured: dict = {}

    async def _fake_verify_file(
        self, artifact_path, *, encrypted=None, record_as=None
    ):
        captured["record_as"] = record_as
        captured["encrypted"] = encrypted
        return {"ok": True, "entries": 1, "tables": 1, "source_file": artifact_path}

    monkeypatch.setattr(backup_cli.RestoreService, "verify_file", _fake_verify_file)

    args = backup_cli.build_parser().parse_args(
        [
            "verify",
            "--from-file",
            "/tmp/renamed.sql.gz",
            "--encrypted",
            "--record-as",
            "148",
        ]
    )
    assert await backup_cli.cmd_verify(args) == 0
    assert captured == {"record_as": 148, "encrypted": True}


@pytest.mark.asyncio
async def test_cmd_verify_from_file_fails_loudly(monkeypatch):
    async def _fake_verify_file(
        self, artifact_path, *, encrypted=None, record_as=None
    ):
        return {"ok": False, "error": "Artifact not found: /tmp/nope.sql.gz"}

    monkeypatch.setattr(backup_cli.RestoreService, "verify_file", _fake_verify_file)

    args = backup_cli.build_parser().parse_args(
        ["verify", "--from-file", "/tmp/nope.sql.gz"]
    )
    assert await backup_cli.cmd_verify(args) == 1


@pytest.mark.asyncio
async def test_cmd_drill_from_file_does_not_look_up_a_backup(monkeypatch):
    """No session, so it works with the database gone."""
    captured: dict = {}

    async def _fake_drill_file(
        self, artifact_path, *, encrypted=None, record_as=None
    ):
        captured["artifact_path"] = artifact_path
        captured["record_as"] = record_as
        return {
            "ok": True,
            "tables_restored": 15,
            "duration_seconds": 3,
            "source_file": artifact_path,
        }

    def _must_not_be_used(*_args, **_kwargs):
        raise AssertionError("drill --from-file must not read the database")

    monkeypatch.setattr(backup_cli.RestoreService, "drill_file", _fake_drill_file)
    monkeypatch.setattr(backup_cli, "AsyncSessionLocal", _must_not_be_used)

    args = backup_cli.build_parser().parse_args(
        ["drill", "--from-file", "/tmp/backup.sql.gz.age", "--record-as", "148"]
    )
    assert await backup_cli.cmd_drill(args) == 0
    assert captured == {
        "artifact_path": "/tmp/backup.sql.gz.age",
        "record_as": 148,
    }


@pytest.mark.asyncio
async def test_cmd_drill_from_file_fails_loudly(monkeypatch):
    async def _fake_drill_file(
        self, artifact_path, *, encrypted=None, record_as=None
    ):
        return {"ok": False, "error": "pg_restore exited with code 1"}

    monkeypatch.setattr(backup_cli.RestoreService, "drill_file", _fake_drill_file)

    args = backup_cli.build_parser().parse_args(
        ["drill", "--from-file", "/tmp/backup.sql.gz"]
    )
    assert await backup_cli.cmd_drill(args) == 1


# ----------------------------------------------------------------------
# verify / drill --from-file: prove a backup usable without the database
# ----------------------------------------------------------------------
#
# The automated verify and drill cannot open an encrypted artifact — the age
# identity is kept off the production host by design — so the strongest
# automatic proof is a checksum. These commands let the operator take the
# artifact to wherever the key is and finish the job.


@pytest.mark.asyncio
async def test_cmd_verify_from_file_needs_no_session(monkeypatch):
    captured: dict = {}

    async def _fake_verify_file(
        self, artifact_path, *, encrypted=None, record_as=None
    ):
        captured["artifact_path"] = artifact_path
        captured["encrypted"] = encrypted
        captured["record_as"] = record_as
        return {"ok": True, "entries": 12, "tables": 9, "source_file": artifact_path}

    monkeypatch.setattr(backup_cli.RestoreService, "verify_file", _fake_verify_file)

    args = backup_cli.build_parser().parse_args(
        ["verify", "--from-file", "/tmp/backup.sql.gz.age"]
    )
    assert await backup_cli.cmd_verify(args) == 0
    assert captured == {
        "artifact_path": "/tmp/backup.sql.gz.age",
        "encrypted": None,
        "record_as": None,
    }


@pytest.mark.asyncio
async def test_cmd_verify_from_file_passes_record_as(monkeypatch):
    """--record-as is how a manual verify reaches the dashboard."""
    captured: dict = {}

    async def _fake_verify_file(
        self, artifact_path, *, encrypted=None, record_as=None
    ):
        captured["record_as"] = record_as
        captured["encrypted"] = encrypted
        return {"ok": True, "entries": 1, "tables": 1, "source_file": artifact_path}

    monkeypatch.setattr(backup_cli.RestoreService, "verify_file", _fake_verify_file)

    args = backup_cli.build_parser().parse_args(
        [
            "verify",
            "--from-file",
            "/tmp/renamed.sql.gz",
            "--encrypted",
            "--record-as",
            "148",
        ]
    )
    assert await backup_cli.cmd_verify(args) == 0
    assert captured == {"record_as": 148, "encrypted": True}


@pytest.mark.asyncio
async def test_cmd_verify_from_file_fails_loudly(monkeypatch):
    async def _fake_verify_file(
        self, artifact_path, *, encrypted=None, record_as=None
    ):
        return {"ok": False, "error": "Artifact not found: /tmp/nope.sql.gz"}

    monkeypatch.setattr(backup_cli.RestoreService, "verify_file", _fake_verify_file)

    args = backup_cli.build_parser().parse_args(
        ["verify", "--from-file", "/tmp/nope.sql.gz"]
    )
    assert await backup_cli.cmd_verify(args) == 1


@pytest.mark.asyncio
async def test_cmd_drill_from_file_does_not_look_up_a_backup(monkeypatch):
    """No session, so it works with the database gone."""
    captured: dict = {}

    async def _fake_drill_file(
        self, artifact_path, *, encrypted=None, record_as=None
    ):
        captured["artifact_path"] = artifact_path
        captured["record_as"] = record_as
        return {
            "ok": True,
            "tables_restored": 15,
            "duration_seconds": 3,
            "source_file": artifact_path,
        }

    def _must_not_be_used(*_args, **_kwargs):
        raise AssertionError("drill --from-file must not read the database")

    monkeypatch.setattr(backup_cli.RestoreService, "drill_file", _fake_drill_file)
    monkeypatch.setattr(backup_cli, "AsyncSessionLocal", _must_not_be_used)

    args = backup_cli.build_parser().parse_args(
        ["drill", "--from-file", "/tmp/backup.sql.gz.age", "--record-as", "148"]
    )
    assert await backup_cli.cmd_drill(args) == 0
    assert captured == {
        "artifact_path": "/tmp/backup.sql.gz.age",
        "record_as": 148,
    }


@pytest.mark.asyncio
async def test_cmd_drill_from_file_fails_loudly(monkeypatch):
    async def _fake_drill_file(
        self, artifact_path, *, encrypted=None, record_as=None
    ):
        return {"ok": False, "error": "pg_restore exited with code 1"}

    monkeypatch.setattr(backup_cli.RestoreService, "drill_file", _fake_drill_file)

    args = backup_cli.build_parser().parse_args(
        ["drill", "--from-file", "/tmp/backup.sql.gz"]
    )
    assert await backup_cli.cmd_drill(args) == 1
