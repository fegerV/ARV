"""Tests for the backup CLI (``app/cli/backup.py``) and the host scripts.

The shell scripts in ``deploy/backup/`` are intentionally thin, but a syntax
error in one of them means the backup silently never runs — so they are parsed
by ``bash -n`` here.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.cli import backup as backup_cli


def _cli_settings(**overrides) -> SimpleNamespace:
    base = {
        "BACKUP_STAGING_DIR": "/var/backups/arv",
        "BACKUP_AGE_RECIPIENT": "age1example",
        "BACKUP_AGE_BINARY": "age",
        "BACKUP_RCLONE_BINARY": "rclone",
        "BACKUP_SECONDARY_RCLONE_REMOTE": "",
        "BACKUP_MAX_AGE_HOURS": 26,
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

    args = backup_cli.build_parser().parse_args(["db"])
    assert await backup_cli.cmd_db(args) == 1


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
    record = SimpleNamespace(id=139, backup_type="db")

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
    record = SimpleNamespace(id=139, backup_type="db")

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
        backup_cli, "SECRET_PATHS", ((str(secret_file), "app/.env"),)
    )
    monkeypatch.setattr(backup_cli, "run_command", _fake_run_command)
    monkeypatch.setattr(backup_cli, "send_heartbeat", _fake_heartbeat)

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
        backup_cli, "SECRET_PATHS", ((str(secret_file), "app/.env"),)
    )
    monkeypatch.setattr(backup_cli, "send_heartbeat", _async_return(True))

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
    monkeypatch.setattr(backup_cli, "SECRET_PATHS", ((str(secret_file), "app/.env"),))
    monkeypatch.setattr(backup_cli, "run_command", _fake_run_command)
    monkeypatch.setattr(backup_cli, "send_heartbeat", _async_return(True))

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

    async def _fake_restore_to(self, backup_id, target_db):
        captured["backup_id"] = backup_id
        captured["target_db"] = target_db
        return {"ok": True}

    monkeypatch.setattr(backup_cli.RestoreService, "restore_to", _fake_restore_to)

    args = backup_cli.build_parser().parse_args(
        ["restore", "42", "--target-db", "vertex_ar_recovered"]
    )
    assert await backup_cli.cmd_restore(args) == 0
    assert captured == {"backup_id": 42, "target_db": "vertex_ar_recovered"}


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
