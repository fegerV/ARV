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
    python -m app.cli.backup verify         # checksum + pg_restore --list (db)
    python -m app.cli.backup verify-media   # restic check (media)
    python -m app.cli.backup drill          # restore into a throwaway database
    python -m app.cli.backup download       # save an artifact to a file
    python -m app.cli.backup restore        # operator-initiated restore
    python -m app.cli.backup status         # last run per backup type
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import sys
import tarfile
import tempfile
import time
from datetime import datetime, UTC

import structlog

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.backup import BackupHistory
from app.services.backup_metrics import record_failure, record_success
from app.services.backup_service import BackupService, _utcnow_naive
from app.services.media_backup_service import MediaBackupService
from app.services.restore_service import (
    ArtifactUnavailable,
    DecryptionUnavailable,
    RestoreService,
)
from app.utils.command import CommandError, run_command
from app.utils.heartbeat import send_heartbeat

logger = structlog.get_logger()

# Filesystem paths holding class-A3 material (secrets and configuration).
# Restoring these BEFORE the database is mandatory: OAuth tokens stored in the
# DB are encrypted with TOKEN_ENCRYPTION_KEY and cannot be decrypted without it.
#
# ``required`` marks the paths without which the archive is worthless. A backup
# that quietly omits ``.env`` is worse than a failed one: it looks like a backup
# until the day it is needed. ``subpaths`` narrows a tree to the parts that
# matter for recovery, which also keeps the walk out of directories the service
# account cannot read.
#
# On /etc/letsencrypt: ``live``, ``archive``, ``accounts``, ``keys`` and ``csr``
# are mode 0700 root-only, so a unit running as ``arv`` can never read them —
# recursing into that tree is what made this job fail with
# ``PermissionError: /etc/letsencrypt/accounts``. Only ``cli.ini`` and
# ``renewal`` are service-readable. The certificates themselves are
# re-issuable with certbot, which is the documented recovery path
# (docs/RESTORE_RUNBOOK.md §7); to capture them as well, run
# ``deploy/backup/backup-secrets.sh`` as root.
SECRET_PATHS: tuple[tuple[str, str, bool, tuple[str, ...]], ...] = (
    (".env", "app/.env", True, ()),
    ("/etc/letsencrypt", "etc/letsencrypt", False, ("cli.ini", "renewal")),
    ("deploy", "deploy", False, ()),
)


# ----------------------------------------------------------------------
# Commands
# ----------------------------------------------------------------------


async def cmd_db(args: argparse.Namespace) -> int:
    """Run a database backup and report the outcome.

    The recipient company and the remote folder default to the values in
    ``system_settings`` (``backup.backup_company_id`` / ``backup.backup_yd_folder``)
    because the dump is shipped through *that company's* Yandex Disk. Resolving
    them here is what makes ``deploy/backup/backup-db.sh`` — and therefore
    ``arv-backup-db.timer`` — usable at all: the in-app scheduler passes
    ``company_id`` explicitly, but the CLI used to default it to ``None`` and
    die with "Yandex Disk provider not available for company_id=None".
    """
    company_id = args.company_id
    yd_folder = args.yd_folder

    if company_id is None or yd_folder is None:
        from app.services.settings_service import SettingsService

        async with AsyncSessionLocal() as session:
            all_settings = await SettingsService(session).get_all_settings()
        backup_settings = all_settings.backup
        if company_id is None:
            company_id = backup_settings.backup_company_id
        if yd_folder is None:
            yd_folder = backup_settings.backup_yd_folder

    if company_id is None:
        print(
            "no backup company configured: pass --company-id or set "
            "'backup_company_id' under Settings -> Backup in the admin panel",
            file=sys.stderr,
        )
        return 2

    service = BackupService()
    record = await service.run_backup(
        company_id=company_id,
        yd_folder=yd_folder or "backups",
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


async def _start_secrets_record(trigger: str) -> int | None:
    """Create the ``backup_history`` row for a secrets run.

    Without a row the A3 job is invisible: ``backup status`` reports
    "secrets: never run" forever, so nothing can alert when it silently stops
    running — the exact blind spot the db and media jobs already avoid.

    Bookkeeping failure must never fail the backup itself, hence the broad
    catch: the archive on disk is what matters, the row is what tells us about
    it.
    """
    try:
        async with AsyncSessionLocal() as session:
            record = BackupHistory(
                started_at=_utcnow_naive(),
                status="running",
                trigger=trigger,
                backup_type="secrets",
                target="primary" if settings.secondary_target_enabled else "local",
                encrypted=bool(settings.encryption_enabled),
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return record.id
    except Exception as exc:  # noqa: BLE001 - never fail the backup for this
        logger.warning("secrets_history_start_failed", error=str(exc))
        return None


async def _finish_secrets_record(
    record_id: int | None,
    *,
    status: str,
    artifact: str | None,
    size_bytes: int | None,
    checksum: str | None,
    duration: int,
    error_message: str | None = None,
) -> None:
    """Stamp the outcome of a secrets run onto its ``backup_history`` row."""
    if record_id is None:
        return
    try:
        async with AsyncSessionLocal() as session:
            record = await session.get(BackupHistory, record_id)
            if record is None:
                return
            record.finished_at = _utcnow_naive()
            record.status = status
            record.size_bytes = size_bytes
            record.checksum = checksum
            record.yd_path = artifact
            record.duration_seconds = duration
            record.error_message = error_message
            await session.commit()
    except Exception as exc:  # noqa: BLE001 - the archive is already on disk
        logger.warning("secrets_history_finish_failed", error=str(exc))


async def cmd_secrets(args: argparse.Namespace) -> int:
    """Archive and encrypt the configuration/secret material (class A3).

    The archive holds ``SECRET_KEY``, so two invariants are enforced here:

    * it is created mode ``0600`` from the first byte — ``tarfile.open(path)``
      would apply the process umask (0644 in practice) and leave the key
      world-readable for the whole run, and permanently if the run died before
      the ``chmod`` at the end;
    * the plaintext tar never survives when encryption is configured, on any
      outcome. A previous version removed it only on the success path, so a
      failure mid-archive left a readable ``.env`` on disk.
    """
    stage = args.stage or settings.BACKUP_STAGING_DIR
    os.makedirs(stage, exist_ok=True)

    # Sub-second precision for the same reason as the db artifact name: two
    # runs in one second would otherwise share a path, and one row's rotation
    # would delete the archive another row still points at.
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    tar_path = os.path.join(stage, f"secrets_{timestamp}.tar.gz")
    encrypted_path = tar_path + ".age"
    missing_required: list[str] = []

    started_monotonic = time.monotonic()
    record_id = await _start_secrets_record(args.trigger)
    backup_type = "secrets"
    target = "primary" if settings.secondary_target_enabled else "local"

    try:
        fd = os.open(tar_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as raw:
            with tarfile.open(fileobj=raw, mode="w:gz") as archive:
                for source, arcname, required, subpaths in SECRET_PATHS:
                    targets = (
                        [
                            (os.path.join(source, sub), f"{arcname}/{sub}")
                            for sub in subpaths
                        ]
                        if subpaths
                        else [(source, arcname)]
                    )
                    for path, name in targets:
                        if not os.path.exists(path):
                            if required:
                                missing_required.append(path)
                            else:
                                logger.warning(
                                    "secrets_backup_path_missing", path=path
                                )
                            continue
                        try:
                            archive.add(path, arcname=name)
                        except OSError as exc:
                            # An unreadable optional tree (root-only
                            # /etc/letsencrypt/live, for instance) must not take
                            # the whole archive down, but it must be visible in
                            # the log rather than silently dropped.
                            if required:
                                raise
                            logger.warning(
                                "secrets_backup_path_unreadable",
                                path=path,
                                error=str(exc),
                            )

        if missing_required:
            raise RuntimeError(
                "required secret paths are missing: " + ", ".join(missing_required)
            )

        if settings.encryption_enabled:
            binary = (settings.BACKUP_AGE_BINARY or "age").strip()
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
            artifact = encrypted_path
        else:
            artifact = tar_path
            logger.warning(
                "secrets_backup_unencrypted",
                reason="BACKUP_AGE_RECIPIENT is not set; the archive holds secrets in the clear",
            )

        os.chmod(artifact, 0o600)

        # Keep a local copy with restrictive permissions; the off-site push is
        # done by the same rclone remote the database dumps use.
        if settings.secondary_target_enabled:
            remote = settings.BACKUP_SECONDARY_RCLONE_REMOTE.rstrip("/")
            rclone = (settings.BACKUP_RCLONE_BINARY or "rclone").strip()
            await run_command(
                [
                    rclone, "copyto", artifact,
                    f"{remote}/secrets/{os.path.basename(artifact)}",
                ],
                label="rclone copyto (secrets)",
                timeout=3600,
            )

        size_bytes = os.path.getsize(artifact)
        checksum = await asyncio.to_thread(BackupService._sha256_file, artifact)
        duration = int(time.monotonic() - started_monotonic)

        await _finish_secrets_record(
            record_id,
            status="success",
            artifact=artifact,
            size_bytes=size_bytes,
            checksum=checksum,
            duration=duration,
        )
        record_success(backup_type, target, size_bytes, duration)

        print(f"secrets archive: {artifact}")
        await send_heartbeat("success", detail=os.path.basename(artifact))
        return 0
    except Exception as exc:
        duration = int(time.monotonic() - started_monotonic)
        await _finish_secrets_record(
            record_id,
            status="failed",
            artifact=None,
            size_bytes=None,
            checksum=None,
            duration=duration,
            error_message=str(exc)[:1000],
        )
        record_failure(backup_type, target)
        raise
    finally:
        if os.path.exists(tar_path):
            if settings.encryption_enabled:
                # Configured to encrypt: a plaintext archive must never survive,
                # whether the run succeeded or died half-way through.
                os.remove(tar_path)
            else:
                # Unencrypted output *is* the artifact, so keep it — but never
                # readable by anyone other than the backup user.
                os.chmod(tar_path, 0o600)


async def cmd_verify(args: argparse.Namespace) -> int:
    """Verify the newest backups: checksum, then archive table of contents.

    Scoped to database dumps on purpose. Both checks below are about a
    ``pg_dump`` custom-format archive, so a ``media`` or ``secrets`` row would
    only ever report a spurious failure — media rows have no ``yd_path`` and no
    ``checksum`` at all, because restic manages its own integrity. Media is
    verified with ``restic check`` (see ``verify-media``) instead.
    """
    if args.from_file:
        # The whole point of this branch: prove an archive is readable without
        # the database, on a machine that has the age key.
        report = await RestoreService().verify_file(
            args.from_file,
            encrypted=True if args.encrypted else None,
            record_as=args.record_as,
        )
        if not report.get("ok"):
            print(f"verify FAILED: {report.get('error')}", file=sys.stderr)
            return 1
        print(
            f"file {args.from_file}: entries={report['entries']} "
            f"tables={report['tables']}"
        )
        return 0

    async with AsyncSessionLocal() as session:
        service = BackupService()
        records = await service.list_backups(
            session, limit=args.limit, backup_type=args.backup_type
        )
        if not records:
            print(
                f"no {args.backup_type} backups to verify",
                file=sys.stderr,
            )
            return 1

        failures = 0
        for record in records:
            # A row with no uploaded artifact — a run that failed before the
            # upload, for instance — has nothing to verify. Calling it a
            # checksum failure would keep the weekly timer red long after the
            # incident recovered; "the newest backup failed" is `status`'s job
            # (and the backup_age metric's), not this command's.
            if not getattr(record, "yd_path", None) or not getattr(
                record, "checksum", None
            ):
                print(
                    f"backup {record.id} ({record.backup_type}): "
                    f"skipped (status={record.status}, no artifact uploaded)"
                )
                continue

            checksum_ok = await service.verify_backup_integrity(record.id)
            listing = await RestoreService().verify_dump(record.id)
            skipped = bool(listing.get("skipped"))
            # A skipped table-of-contents check is not a failure. The artifact
            # is encrypted and the age identity is not on this host by design,
            # so the archive cannot be opened here; the checksum still proves
            # the bytes survived the trip to object storage.
            ok = checksum_ok and (bool(listing.get("ok")) or skipped)
            toc_text = "ok" if listing.get("ok") else ("skipped" if skipped else "FAIL")
            print(
                f"backup {record.id} ({record.backup_type}): "
                f"checksum={'ok' if checksum_ok else 'FAIL'} "
                f"toc={toc_text} "
                f"entries={listing.get('entries', 0)}"
            )
            if not ok:
                failures += 1

    return 0 if failures == 0 else 1


async def cmd_verify_media(args: argparse.Namespace) -> int:
    """Check the restic media repository for corruption (``restic check``).

    ``--read-data-subset`` re-reads and re-hashes a slice of the repository
    from the backend. That is the only way to catch bit rot or a silently
    truncated upload; a plain ``restic check`` only validates metadata.
    """
    service = MediaBackupService()
    if not service.available():
        print(
            "media backup is not configured "
            "(set BACKUP_MEDIA_ENABLED and BACKUP_RESTIC_REPOSITORY)",
            file=sys.stderr,
        )
        return 2

    subset = args.read_data_subset
    ok = await service.check_integrity(read_data_subset=subset)
    print(f"media repository check (read-data-subset={subset}): {'ok' if ok else 'FAIL'}")
    return 0 if ok else 1


async def cmd_drill(args: argparse.Namespace) -> int:
    """Restore the newest backup into a throwaway database."""
    if args.from_file:
        # The only way to actually prove a backup restorable while the age
        # identity stays off the production host: run the drill where the key
        # is. --record-as lets that drill clear the 'drill overdue' alert.
        report = await RestoreService().drill_file(
            args.from_file,
            encrypted=True if args.encrypted else None,
            record_as=args.record_as,
        )
        if report.get("ok"):
            print(
                f"drill on {args.from_file}: {report['tables_restored']} tables "
                f"restored in {report['duration_seconds']}s "
                f"(throwaway database dropped)"
            )
            return 0
        print(f"drill FAILED: {report.get('error')}", file=sys.stderr)
        return 1

    async with AsyncSessionLocal() as session:
        record = await BackupService().get_last_status(
            session, backup_type=args.backup_type
        )
    if record is None:
        print(f"no {args.backup_type} backup available for a drill", file=sys.stderr)
        return 1

    report = await RestoreService().restore_drill(record.id)
    print(f"drill on backup {record.id}: {report}")
    if report.get("skipped"):
        # Not a failure: the backup is encrypted and the age identity is off
        # the host (see RestoreService.STATUS_NO_IDENTITY). Returning non-zero
        # would trip OnFailure= on the timer every month for a healthy backup.
        return 0
    return 0 if report.get("ok") else 1


def _print_cutover_hint(target_db: str) -> None:
    """Print the steps that remain after a successful restore.

    The restore is now a single command; what is left is the part that changes
    production, and that must stay deliberate. Printing it here means an
    operator in the middle of an incident does not have to go and read the
    runbook to find the exact lines — which is when runbooks get skimmed and
    steps get skipped.
    """
    print(
        "\nRestored into a separate database. Production is NOT changed yet.\n"
        f"  1. sanity-check the data:\n"
        f"       sudo -u postgres psql -d {target_db} -c 'SELECT count(*) FROM ar_content'\n"
        f"  2. cut over (stops the app, keeps a .env backup, smoke-tests, prints rollback):\n"
        f"       sudo -u arv /opt/arv/app/deploy/backup/recover.sh --cutover --target-db {target_db}\n"
        f"  3. rollback at any point: restore DATABASE_URL from the .env backup and restart."
    )


async def cmd_restore(args: argparse.Namespace) -> int:
    """Restore a backup into a separate database.

    Two sources, one outcome. ``--from-file`` restores an artifact the operator
    already has, which is the only route that works when the database is gone:
    the normal path resolves its storage token *from* that database, so it
    cannot be the way back from losing it.
    """
    if not args.target_db:
        print("--target-db is required", file=sys.stderr)
        return 2

    if args.from_file:
        if args.backup_id is not None:
            print(
                "pass either a backup id or --from-file, not both",
                file=sys.stderr,
            )
            return 2
        report = await RestoreService().restore_from_file(
            args.from_file,
            args.target_db,
            create_if_missing=args.create_db,
            encrypted=True if args.encrypted else None,
        )
        source = args.from_file
    else:
        if args.backup_id is None:
            print("a backup id or --from-file is required", file=sys.stderr)
            return 2
        report = await RestoreService().restore_to(
            args.backup_id,
            args.target_db,
            create_if_missing=args.create_db,
        )
        source = f"backup {args.backup_id}"

    if not report.get("ok"):
        print(f"restore FAILED: {report.get('error')}", file=sys.stderr)
        return 1

    created = " (database was created)" if report.get("created_database") else ""
    print(
        f"restore ok: {report['tables_restored']} tables from {source} -> "
        f"{report['target_database']} in {report['duration_seconds']}s{created}"
    )
    _print_cutover_hint(report["target_database"])
    return 0


async def cmd_download(args: argparse.Namespace) -> int:
    """Save a backup artifact to a file without restoring it.

    Exists so a backup can be carried off the host — to a second site, another
    machine, or an operator's workstation — without going through the Yandex
    Disk web interface. That interface is exactly what is unavailable when the
    database holding the storage token is the thing that was lost.
    """
    service = RestoreService()
    workdir = tempfile.mkdtemp(prefix="arv-download-")
    try:
        try:
            info = await service.fetch_artifact(
                args.backup_id, workdir, decrypt=args.decrypt
            )
        except ArtifactUnavailable as exc:
            print(f"cannot download backup {args.backup_id}: {exc}", file=sys.stderr)
            return 2
        except DecryptionUnavailable as exc:
            print(f"cannot decrypt backup {args.backup_id}: {exc}", file=sys.stderr)
            return 2

        output = args.output
        if not output:
            output = os.path.join(os.getcwd(), info["filename"])
        elif os.path.isdir(output):
            output = os.path.join(output, info["filename"])

        await asyncio.to_thread(shutil.copyfile, info["path"], output)
        # An artifact carrying SECRET_KEY must not land world-readable just
        # because the umask said so.
        os.chmod(output, 0o600)

        state = "plaintext" if info["plaintext"] else "age-encrypted"
        print(f"saved {info['filename']} -> {output} ({info['size_bytes']} bytes, {state})")
        if not info["plaintext"]:
            print(
                "note: the private key is not on this host by design. Decrypt "
                "where it lives:\n"
                f"  age --decrypt --identity <key> -o dump.gz {output}"
            )
        return 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


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
    """Print the most recent run per backup type (operational dashboard).

    Each type gets its own staleness limit: the database and media jobs run
    daily, the secrets archive weekly. Applying the daily limit to a weekly job
    would report it as stale six days out of seven, which is a false alarm that
    teaches operators to ignore the output.
    """
    service = BackupService()
    exit_code = 0

    daily = getattr(settings, "BACKUP_MAX_AGE_HOURS", 26)
    limits = {
        "db": daily,
        "media": daily,
        "secrets": getattr(settings, "BACKUP_SECRETS_MAX_AGE_HOURS", 8 * 24),
    }

    async with AsyncSessionLocal() as session:
        for backup_type, max_age_hours in limits.items():
            record = await service.get_last_status(session, backup_type=backup_type)
            if record is None:
                print(f"{backup_type}: never run")
                exit_code = 1
                continue

            age_hours = _age_hours(record.finished_at or record.started_at)
            stale = age_hours is not None and age_hours > max_age_hours
            if stale or record.status != "success":
                exit_code = 1

            age_text = f"{age_hours:.1f}h" if age_hours is not None else "unknown"
            print(
                f"{backup_type}: status={record.status} age={age_text} "
                f"(limit {max_age_hours}h){' STALE' if stale else ''}"
            )
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


def _add_from_file_args(
    parser: argparse.ArgumentParser, *, with_record_as: bool = True
) -> None:
    """Add the ``--from-file`` options shared by verify, drill and restore.

    Defined once so the three commands cannot drift apart in how they describe
    or interpret the same options. ``with_record_as`` is off for restore, which
    writes no verification status to record.
    """
    parser.add_argument(
        "--from-file",
        default=None,
        metavar="PATH",
        help=(
            "Operate on an artifact already on this host instead of fetching "
            "it from storage. Needs no database."
        ),
    )
    parser.add_argument(
        "--encrypted",
        action="store_true",
        help=(
            "Force treating the artifact as age-encrypted. Only needed when "
            "the file was renamed away from its .age suffix."
        ),
    )
    if with_record_as:
        parser.add_argument(
            "--record-as",
            type=int,
            default=None,
            metavar="BACKUP_ID",
            help=(
                "Also write the outcome onto this backup_history row, so a "
                "manual drill can clear the 'drill overdue' alert. Requires "
                "the database."
            ),
        )


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
    db.add_argument(
        "--yd-folder",
        default=None,
        help="Defaults to the configured backup.backup_yd_folder.",
    )
    db.set_defaults(func=cmd_db)

    media = sub.add_parser("media", help="Snapshot media originals with restic.")
    media.set_defaults(func=cmd_media)

    secrets = sub.add_parser("secrets", help="Archive and encrypt .env / TLS material.")
    secrets.add_argument("--stage", default=None)
    secrets.set_defaults(func=cmd_secrets)

    verify = sub.add_parser("verify", help="Verify recent backups end to end.")
    verify.add_argument("--limit", type=int, default=1)
    verify.add_argument(
        "--backup-type",
        default="db",
        choices=("db",),
        help="Only database dumps have a pg_restore-verifiable archive.",
    )
    _add_from_file_args(verify)
    verify.set_defaults(func=cmd_verify)

    verify_media = sub.add_parser(
        "verify-media", help="Check the restic media repository for corruption."
    )
    verify_media.add_argument("--read-data-subset", default="5%")
    verify_media.set_defaults(func=cmd_verify_media)

    drill = sub.add_parser("drill", help="Restore into a throwaway database.")
    drill.add_argument("--backup-type", default="db")
    _add_from_file_args(drill)
    drill.set_defaults(func=cmd_drill)

    restore = sub.add_parser("restore", help="Restore a backup into a target database.")
    restore.add_argument(
        "backup_id",
        type=int,
        nargs="?",
        default=None,
        help="Backup id to fetch from storage. Omit when using --from-file.",
    )
    restore.add_argument("--target-db", required=True)
    restore.add_argument(
        "--create-db",
        action="store_true",
        help="Create the target database when it does not exist.",
    )
    _add_from_file_args(restore, with_record_as=False)
    restore.set_defaults(func=cmd_restore)

    download = sub.add_parser(
        "download", help="Save a backup artifact to a file (no restore)."
    )
    download.add_argument("backup_id", type=int)
    download.add_argument(
        "--output",
        "-o",
        default=None,
        help="Destination file or directory (default: current directory).",
    )
    download.add_argument(
        "--decrypt",
        action="store_true",
        help="Decrypt with BACKUP_AGE_IDENTITY_FILE when it is available.",
    )
    download.set_defaults(func=cmd_download)

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
