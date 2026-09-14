"""Command-line entry points for backup and disaster-recovery operations.

The host-level shell scripts in ``deploy/backup/`` are deliberately thin: they
handle locking, filesystem permissions and exit codes, and delegate the actual
work to the services below. Keeping the logic in Python means the same code
paths are covered by the test suite instead of being re-implemented in bash
where nothing tests them.

Usage::

    python -m app.cli.backup db             # database dump
    python -m app.cli.backup media          # restic snapshot of media
    python -m app.cli.backup secrets        # tar + age of .env / TLS material
    python -m app.cli.backup verify         # checksum + pg_restore --list
    python -m app.cli.backup drill          # restore into a throwaway database
    python -m app.cli.backup restore        # operator-initiated restore
    python -m app.cli.backup status         # last run per backup type
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tarfile
import tempfile
from datetime import datetime, UTC

import structlog

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.backup import BackupHistory
from app.services.backup_service import BackupService
from app.services.media_backup_service import MediaBackupService
from app.services.restore_service import RestoreService
from app.utils.command import CommandError, run_command
from app.utils.heartbeat import send_heartbeat

logger = structlog.get_logger()

# Filesystem paths holding class-A3 material (secrets and configuration).
# Restoring these BEFORE the database is mandatory: OAuth tokens stored in the
# DB are encrypted with TOKEN_ENCRYPTION_KEY and cannot be decrypted without it.
SECRET_PATHS: tuple[tuple[str, str], ...] = (
    (".env", "app/.env"),
    ("/etc/letsencrypt", "etc/letsencrypt"),
    ("deploy", "deploy"),
)


# ----------------------------------------------------------------------
# Commands
# ----------------------------------------------------------------------


async def cmd_db(args: argparse.Namespace) -> int:
    """Run a database backup and report the outcome."""
    service = BackupService()
    record = await service.run_backup(
        company_id=args.company_id,
        yd_folder=args.yd_folder,
        trigger=args.trigger,
        backup_type="db",
    )
    _print_record(record)
    return 0 if record and record.status == "success" else 1


async def cmd_media(args: argparse.Namespace) -> int:
    """Snapshot media originals with restic."""
    service = MediaBackupService()
    if not service.available():
        print(
            "media backup is not configured "
            "(set BACKUP_MEDIA_ENABLED and BACKUP_RESTIC_REPOSITORY)",
            file=sys.stderr,
        )
        return 2

    record = await service.run_backup(trigger=args.trigger)
    _print_record(record)
    return 0 if record and record.status == "success" else 1


async def cmd_secrets(args: argparse.Namespace) -> int:
    """Archive and encrypt the configuration/secret material (class A3)."""
    stage = args.stage or settings.BACKUP_STAGING_DIR
    os.makedirs(stage, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    tar_path = os.path.join(stage, f"secrets_{timestamp}.tar.gz")

    with tarfile.open(tar_path, "w:gz") as archive:
        for source, arcname in SECRET_PATHS:
            if not os.path.exists(source):
                logger.warning("secrets_backup_path_missing", path=source)
                continue
            archive.add(source, arcname=arcname)

    artifact = tar_path
    if settings.encryption_enabled:
        encrypted_path = tar_path + ".age"
        binary = (settings.BACKUP_AGE_BINARY or "age").strip()
        try:
            await run_command(
                [
                    binary, "--encrypt",
                    "--recipient", settings.BACKUP_AGE_RECIPIENT,
                    "--output", encrypted_path,
                    tar_path,
                ],
                label="age --encrypt (secrets)",
                timeout=600,
            )
        finally:
            if os.path.exists(tar_path):
                os.remove(tar_path)
        artifact = encrypted_path
    else:
        logger.warning(
            "secrets_backup_unencrypted",
            reason="BACKUP_AGE_RECIPIENT is not set; the archive holds secrets in the clear",
        )

    # Keep a local copy with restrictive permissions; the off-site push is done
    # by the same rclone remote the database dumps use.
    os.chmod(artifact, 0o600)
    if settings.secondary_target_enabled:
        remote = settings.BACKUP_SECONDARY_RCLONE_REMOTE.rstrip("/")
        rclone = (settings.BACKUP_RCLONE_BINARY or "rclone").strip()
        await run_command(
            [rclone, "copyto", artifact, f"{remote}/secrets/{os.path.basename(artifact)}"],
            label="rclone copyto (secrets)",
            timeout=3600,
        )

    print(f"secrets archive: {artifact}")
    await send_heartbeat("success", detail=os.path.basename(artifact))
    return 0


async def cmd_verify(args: argparse.Namespace) -> int:
    """Verify the newest backups: checksum, then archive table of contents."""
    async with AsyncSessionLocal() as session:
        service = BackupService()
        records = await service.list_backups(session, limit=args.limit)
        if not records:
            print("no backups to verify", file=sys.stderr)
            return 1

        failures = 0
        for record in records:
            checksum_ok = await service.verify_backup_integrity(record.id)
            listing = await RestoreService().verify_dump(record.id)
            ok = checksum_ok and listing.get("ok", False)
            print(
                f"backup {record.id} ({record.backup_type}): "
                f"checksum={'ok' if checksum_ok else 'FAIL'} "
                f"toc={'ok' if listing.get('ok') else 'FAIL'} "
                f"entries={listing.get('entries', 0)}"
            )
            if not ok:
                failures += 1

    return 0 if failures == 0 else 1


async def cmd_drill(args: argparse.Namespace) -> int:
    """Restore the newest backup into a throwaway database."""
    async with AsyncSessionLocal() as session:
        record = await BackupService().get_last_status(
            session, backup_type=args.backup_type
        )
    if record is None:
        print(f"no {args.backup_type} backup available for a drill", file=sys.stderr)
        return 1

    report = await RestoreService().restore_drill(record.id)
    print(f"drill on backup {record.id}: {report}")
    return 0 if report.get("ok") else 1


async def cmd_restore(args: argparse.Namespace) -> int:
    """Restore a specific backup into a separate database."""
    if not args.target_db:
        print("--target-db is required", file=sys.stderr)
        return 2

    report = await RestoreService().restore_to(args.backup_id, args.target_db)
    print(f"restore: {report}")
    return 0 if report.get("ok") else 1


async def cmd_notify(args: argparse.Namespace) -> int:
    """Send an admin alert about a failed backup job.

    Wired to systemd's ``OnFailure=`` so a failing timer reports itself. The
    alert is sent from this short-lived process rather than from the web
    application, because the application may be exactly what is broken.
    """
    from app.services.alert_service import Alert, send_critical_alerts

    unit = args.unit or "arv-backup"
    detail = args.detail or "job failed"
    # The unit name goes into the message itself, not just the metrics: an
    # operator reading a Telegram alert must see which job failed without
    # opening the dashboard.
    message = f"{unit}: {detail}"

    await send_critical_alerts(
        [
            Alert(
                severity="critical",
                title="Backup job failed",
                message=message,
                metrics={"unit": unit},
                affected_services=["backup"],
            )
        ],
        {"unit": unit},
    )

    # Also trip the external dead-man's-switch: an alert raised by the host
    # itself is worthless if the host is what died.
    await send_heartbeat("fail", detail=message)
    print(f"alert sent for {unit}")
    return 0


async def cmd_status(args: argparse.Namespace) -> int:
    """Print the most recent run per backup type (operational dashboard)."""
    service = BackupService()
    exit_code = 0

    async with AsyncSessionLocal() as session:
        for backup_type in ("db", "media", "secrets"):
            record = await service.get_last_status(session, backup_type=backup_type)
            if record is None:
                print(f"{backup_type}: never run")
                exit_code = 1
                continue

            age_hours = _age_hours(record.finished_at or record.started_at)
            stale = age_hours is not None and age_hours > settings.BACKUP_MAX_AGE_HOURS
            if stale or record.status != "success":
                exit_code = 1

            age_text = f"{age_hours:.1f}h" if age_hours is not None else "unknown"
            print(f"{backup_type}: status={record.status} age={age_text}")
            print(
                f"    verified_at={record.verified_at} "
                f"verification={record.verification_status} "
                f"restore_tested_at={record.restore_tested_at} "
                f"restore_test={record.restore_test_status}"
            )

    return exit_code


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _age_hours(when: datetime | None) -> float | None:
    if when is None:
        return None
    return (datetime.now(UTC).replace(tzinfo=None) - when).total_seconds() / 3600.0


def _print_record(record: BackupHistory | None) -> None:
    if record is None:
        print("backup skipped (not configured)", file=sys.stderr)
        return
    print(
        f"backup {record.id}: status={record.status} "
        f"type={record.backup_type} target={record.target} "
        f"encrypted={record.encrypted} size={record.size_bytes} "
        f"duration={record.duration_seconds}s path={record.yd_path}"
    )
    if record.error_message:
        print(f"error: {record.error_message}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli.backup",
        description="ARV backup and disaster-recovery operations.",
    )
    parser.add_argument(
        "--trigger",
        default="scheduled",
        choices=("scheduled", "manual"),
        help="Value recorded in backup_history.trigger (default: scheduled).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    db = sub.add_parser("db", help="Back up the PostgreSQL database.")
    db.add_argument("--company-id", type=int, default=None)
    db.add_argument("--yd-folder", default="backups")
    db.set_defaults(func=cmd_db)

    media = sub.add_parser("media", help="Snapshot media originals with restic.")
    media.set_defaults(func=cmd_media)

    secrets = sub.add_parser("secrets", help="Archive and encrypt .env / TLS material.")
    secrets.add_argument("--stage", default=None)
    secrets.set_defaults(func=cmd_secrets)

    verify = sub.add_parser("verify", help="Verify recent backups end to end.")
    verify.add_argument("--limit", type=int, default=1)
    verify.set_defaults(func=cmd_verify)

    drill = sub.add_parser("drill", help="Restore into a throwaway database.")
    drill.add_argument("--backup-type", default="db")
    drill.set_defaults(func=cmd_drill)

    restore = sub.add_parser("restore", help="Restore a backup into a target database.")
    restore.add_argument("backup_id", type=int)
    restore.add_argument("--target-db", required=True)
    restore.set_defaults(func=cmd_restore)

    status = sub.add_parser("status", help="Show the last run per backup type.")
    status.set_defaults(func=cmd_status)

    notify = sub.add_parser("notify", help="Alert admins about a failed job.")
    notify.add_argument("--unit", default="arv-backup")
    notify.add_argument("--detail", default=None)
    notify.set_defaults(func=cmd_notify)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return asyncio.run(args.func(args))
    except CommandError as exc:
        print(f"backup command failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
