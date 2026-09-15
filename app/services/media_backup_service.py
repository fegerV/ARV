"""Media (original uploads) backup via ``restic``.

Why restic rather than copying files
------------------------------------
The ARV design doc (``docs/BACKUP_AND_RECOVERY.md`` §2.1, §8.4) identifies
uploaded photo/video originals as class **A2**: the largest and least
recoverable dataset (~125 GB per 1000 AR contents) — a lost original cannot be
re-uploaded by the customer. A nightly full copy would be slow and expensive.
restic provides, with one mature binary:

* incremental, **deduplicated** snapshots (only changed chunks are shipped);
* **client-side encryption** (AES-256-CTR + Poly1305) with the key never
  leaving the host's ``RESTIC_PASSWORD_FILE``;
* ``restic check --read-data-subset`` for real integrity verification;
* ``restic forget --keep-daily/-weekly/-monthly/-yearly --prune`` — the same
  GFS ladder the database dumps use, so both datasets share one retention model;
* point-in-time restore of a *single* AR content
  (``restic restore --include /VertexAR/<project>/<order>``), which is the
  common partial-recovery case in the runbook (§10.2).

The service is deliberately thin: it orchestrates restic and records the
outcome in ``backup_history`` with ``backup_type='media'``, so media backups
appear in the same monitoring and alerting surface as database backups.
"""

from __future__ import annotations

import asyncio
import json
import socket
import time
from datetime import datetime, UTC

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.backup import BackupHistory
from app.services.backup_metrics import record_failure, record_success, record_verification
from app.utils.command import CommandError, binary_available, run_command
from app.utils.heartbeat import send_heartbeat

logger = structlog.get_logger()


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class MediaBackupService:
    """Snapshot media originals into a restic repository."""

    BACKUP_TIMEOUT: int = 6 * 3600   # 6 hours for the first full snapshot
    FORGET_TIMEOUT: int = 3600
    CHECK_TIMEOUT: int = 3 * 3600

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _restic_env() -> dict[str, str]:
        """Environment for restic: repository + password file (never a literal)."""
        env: dict[str, str] = {}
        repository = (getattr(settings, "BACKUP_RESTIC_REPOSITORY", "") or "").strip()
        if repository:
            env["RESTIC_REPOSITORY"] = repository
        password_file = (
            getattr(settings, "BACKUP_RESTIC_PASSWORD_FILE", "") or ""
        ).strip()
        if password_file:
            env["RESTIC_PASSWORD_FILE"] = password_file
        return env

    @staticmethod
    def _binary() -> str:
        return (getattr(settings, "BACKUP_RESTIC_BINARY", "restic") or "restic").strip()

    @classmethod
    def available(cls) -> bool:
        """True when media backup is enabled and fully configured.

        Checked up front so a scheduled run reports a clear reason instead of
        failing halfway through with an opaque restic error.
        """
        if not getattr(settings, "BACKUP_MEDIA_ENABLED", False):
            return False
        if not (getattr(settings, "BACKUP_RESTIC_REPOSITORY", "") or "").strip():
            return False
        return binary_available(cls._binary())

    @staticmethod
    def _gfs_args() -> list[str]:
        """Build the GFS ``--keep-*`` arguments from configuration."""
        return [
            "--keep-daily", str(getattr(settings, "BACKUP_KEEP_DAILY", 7)),
            "--keep-weekly", str(getattr(settings, "BACKUP_KEEP_WEEKLY", 4)),
            "--keep-monthly", str(getattr(settings, "BACKUP_KEEP_MONTHLY", 12)),
            "--keep-yearly", str(getattr(settings, "BACKUP_KEEP_YEARLY", 3)),
        ]

    # ------------------------------------------------------------------
    # Backup
    # ------------------------------------------------------------------

    async def run_backup(
        self,
        trigger: str = "scheduled",
        session: AsyncSession | None = None,
    ) -> BackupHistory | None:
        """Create a restic snapshot of all configured media paths.

        Returns the ``BackupHistory`` row, or ``None`` when media backup is not
        configured (no noise rows for disabled deployments).
        """
        if not self.available():
            logger.warning(
                "media_backup_skipped",
                reason="BACKUP_MEDIA_ENABLED off or restic repository not configured",
            )
            return None

        paths = [p for p in settings.backup_media_paths if p]
        if not paths:
            logger.warning("media_backup_skipped", reason="no media paths configured")
            return None

        owns_session = session is None
        if owns_session:
            session = AsyncSessionLocal()

        started = time.monotonic()
        record = BackupHistory(
            started_at=_utcnow_naive(),
            status="running",
            trigger=trigger,
            backup_type="media",
            target="primary",
            encrypted=True,  # restic always encrypts its repository
            app_commit=await asyncio.to_thread(self._app_commit),
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        record_id = record.id

        result: BackupHistory | None = None
        try:
            snapshot_id, bytes_processed = await self._snapshot(paths)
            duration = int(time.monotonic() - started)

            rec = await session.get(BackupHistory, record_id)
            if rec:
                rec.finished_at = _utcnow_naive()
                rec.status = "success"
                rec.snapshot_id = snapshot_id
                rec.size_bytes = bytes_processed
                rec.duration_seconds = duration
                await session.commit()
            result = rec

            record_success("media", "primary", bytes_processed, duration)
            logger.info(
                "media_backup_completed",
                snapshot_id=snapshot_id,
                size_bytes=bytes_processed,
                duration_seconds=duration,
            )

            # Rotation is part of the same job: an unreferenced snapshot that is
            # never pruned silently inflates the bill and the restore time.
            try:
                await self._forget()
            except CommandError as exc:
                logger.warning("media_backup_forget_failed", error=str(exc))

            await send_heartbeat("success", detail=f"media:{snapshot_id}")
        except Exception as exc:
            duration = int(time.monotonic() - started)
            logger.error("media_backup_failed", error=str(exc), exc_info=True)
            rec = await session.get(BackupHistory, record_id)
            if rec:
                rec.finished_at = _utcnow_naive()
                rec.status = "failed"
                rec.error_message = str(exc)[:1000]
                rec.duration_seconds = duration
                await session.commit()
            result = rec
            record_failure("media", "primary")
            await send_heartbeat("fail", detail=f"media:{str(exc)[:200]}")
        finally:
            # Read the record *before* the session closes. A ``session.get()``
            # issued after ``close()`` opens a fresh transaction on a new pooled
            # connection that is then never checked in, so the garbage collector
            # tears it down at interpreter exit — which is why every scheduled
            # run logged "greenlet is being finalized" plus an SAWarning.
            # ``backup_service.run_backup`` reads inside its ``try`` for the
            # same reason.
            if owns_session:
                await session.close()

        return result

    async def _snapshot(self, paths: list[str]) -> tuple[str | None, int | None]:
        """Run ``restic backup`` and parse the summary message.

        Returns ``(snapshot_id, total_bytes_processed)``.
        """
        cmd = [
            self._binary(),
            "backup",
            *paths,
            "--tag", "media",
            "--host", socket.gethostname(),
            "--json",
        ]
        stdout = await run_command(
            cmd,
            label="restic backup",
            timeout=self.BACKUP_TIMEOUT,
            env=self._restic_env(),
            capture_stdout=True,
        )

        snapshot_id: str | None = None
        bytes_processed: int | None = None
        # `restic backup --json` streams one JSON object per line; the final
        # "summary" message carries the snapshot id and byte counters.
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if payload.get("message_type") != "summary":
                continue
            snapshot_id = payload.get("snapshot_id") or snapshot_id
            total = payload.get("total_bytes_processed")
            if isinstance(total, int):
                bytes_processed = total

        if snapshot_id is None:
            logger.warning("media_backup_no_snapshot_id_in_output")
        return snapshot_id, bytes_processed

    async def _forget(self) -> None:
        """Apply the GFS ladder to the restic repository."""
        cmd = [self._binary(), "forget", *self._gfs_args(), "--prune"]
        await run_command(
            cmd,
            label="restic forget",
            timeout=self.FORGET_TIMEOUT,
            env=self._restic_env(),
        )

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    async def check_integrity(self, read_data_subset: str = "5%") -> bool:
        """Run ``restic check`` and record the outcome.

        ``--read-data-subset`` re-reads and re-hashes a random slice of the
        repository from the backend, which is the only way to detect bit rot or
        a silently truncated upload. A full ``--read-data`` pass is reserved for
        the monthly drill because it downloads the whole repository.
        """
        if not self.available():
            return False

        try:
            await run_command(
                [self._binary(), "check", f"--read-data-subset={read_data_subset}"],
                label="restic check",
                timeout=self.CHECK_TIMEOUT,
                env=self._restic_env(),
            )
            ok = True
        except CommandError as exc:
            logger.error("media_backup_check_failed", error=str(exc))
            ok = False

        record_verification("media", ok)
        await self._mark_verified(ok)
        return ok

    async def _mark_verified(self, ok: bool) -> None:
        """Stamp the newest successful media backup with the check result."""
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            stmt = (
                select(BackupHistory)
                .where(
                    BackupHistory.backup_type == "media",
                    BackupHistory.status == "success",
                )
                .order_by(BackupHistory.started_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            if record is None:
                return
            record.verified_at = _utcnow_naive()
            record.verification_status = "ok" if ok else "restore_failed"
            await session.commit()

    async def list_snapshots(self) -> list[dict]:
        """Return restic snapshots as parsed JSON (used by the runbook/UI)."""
        if not self.available():
            return []
        stdout = await run_command(
            [self._binary(), "snapshots", "--json"],
            label="restic snapshots",
            timeout=self.FORGET_TIMEOUT,
            env=self._restic_env(),
            capture_stdout=True,
        )
        try:
            data = json.loads(stdout or "[]")
        except json.JSONDecodeError:
            return []
        return data if isinstance(data, list) else []

    @staticmethod
    def _app_commit() -> str | None:
        from app.services.backup_service import BackupService

        return BackupService._app_commit()
