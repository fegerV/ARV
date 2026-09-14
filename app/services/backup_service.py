"""Service for creating, encrypting, shipping and rotating PostgreSQL backups.

Pipeline implemented here (see ``docs/BACKUP_AND_RECOVERY.md``)::

    pg_dump -Fc  ->  gzip  ->  [age]  ->  primary (Yandex Disk)
                                        \\-> secondary (independent rclone remote)

Design notes
------------
* ``pg_dump`` uses the **custom format** (``-Fc``). Unlike the previous
  plain-text dump it supports ``pg_restore --list`` (validity check without a
  server) and parallel/selective restore, which is what the RTO target of
  ``<= 2 h`` depends on.
* The artifact is **encrypted with ``age`` before it leaves the host** whenever
  ``BACKUP_AGE_RECIPIENT`` is set. The matching private key must never live on
  this server.
* A **second, independent off-site copy** is pushed through ``rclone`` to a
  remote hosted by a *different* provider than the one holding production
  media — otherwise a single compromised account destroys both the data and
  its backup.
* Rotation follows a **GFS ladder** (7 daily / 4 weekly / 12 monthly /
  3 yearly) instead of "keep the N newest", so a restore point from a month
  ago still exists when damage is noticed late.
* Every outcome is published to Prometheus and, on completion, pinged to an
  external dead-man's-switch: a host that is entirely down stops emitting
  metrics, and "no data" is not an alert.
"""

from __future__ import annotations

import asyncio
import gzip
import hashlib
import os
import subprocess
import tempfile
import time
from datetime import datetime, timedelta, UTC
from typing import Optional
from urllib.parse import urlparse

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.storage_providers import get_provider_for_company
from app.core.yandex_disk_provider import YandexDiskStorageProvider
from app.models.backup import BackupHistory
from app.models.company import Company
from app.services.backup_metrics import (
    record_failure,
    record_success,
    record_verification,
)
from app.services.backup_rotation import (
    DEFAULT_KEEP_DAILY,
    DEFAULT_KEEP_MONTHLY,
    DEFAULT_KEEP_WEEKLY,
    DEFAULT_KEEP_YEARLY,
    select_gfs_deletes,
)
from app.utils.command import run_command
from app.utils.heartbeat import send_heartbeat

logger = structlog.get_logger()

# Artifact naming is kept stable on purpose: ``backup_<ts>.sql.gz`` is the
# contract the backups UI and the operational runbooks already rely on, even
# though the payload is now a custom-format dump rather than plain SQL.
ARTIFACT_SUFFIX = ".sql.gz"
ARTIFACT_SUFFIX_ENCRYPTED = ".sql.gz.age"


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _parse_database_url(url: str) -> dict:
    """Extract connection parameters from a SQLAlchemy DATABASE_URL.

    Strips the ``+asyncpg`` driver suffix so that ``urlparse`` handles
    the scheme correctly.

    Returns:
        Dict with keys ``host``, ``port``, ``dbname``, ``user``, ``password``.
    """
    cleaned = url.replace("+asyncpg", "").replace("+aiosqlite", "")
    parsed = urlparse(cleaned)
    return {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "dbname": (parsed.path or "/postgres").lstrip("/"),
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
    }


class BackupService:
    """Orchestrates database backup lifecycle."""

    # Maximum time (seconds) to wait for pg_dump before killing it.
    PG_DUMP_TIMEOUT: int = 600  # 10 minutes
    # Maximum time (seconds) for an external copy (rclone/age).
    COPY_TIMEOUT: int = 3600

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_backup(
        self,
        session: AsyncSession | None = None,
        company_id: int = None,
        yd_folder: str = "backups",
        trigger: str = "manual",
        backup_type: str = "db",
    ) -> BackupHistory:
        """Execute a full backup: dump, compress, encrypt, ship, record.

        Args:
            session: Optional database session. Created internally if not provided.
            company_id: Company whose Yandex Disk token will be used.
            yd_folder: Target folder on the primary remote.
            trigger: ``"manual"`` or ``"scheduled"``.
            backup_type: ``"db"`` (default), ``"media"``, ``"secrets"``, ``"config"``.

        Returns:
            The ``BackupHistory`` record with the outcome.
        """
        log = logger.bind(company_id=company_id, trigger=trigger)
        log.info("backup_started", backup_type=backup_type)

        started_monotonic = time.monotonic()
        encryption_enabled = bool(getattr(settings, "encryption_enabled", False))
        secondary_enabled = bool(getattr(settings, "secondary_target_enabled", False))

        owns_session = False
        if session is None:
            owns_session = True
            session = AsyncSessionLocal()

        try:
            record = BackupHistory(
                started_at=_utcnow_naive(),
                status="running",
                company_id=company_id,
                trigger=trigger,
                backup_type=backup_type,
                target="primary",
                encrypted=encryption_enabled,
                app_commit=await asyncio.to_thread(self._app_commit),
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            record_id = record.id

            tmp_path: str | None = None
            gz_path: str | None = None
            enc_path: str | None = None

            try:
                # 1. pg_dump (custom format)
                tmp_path = await self._run_pg_dump()
                os.path.getsize(tmp_path)  # ensure file exists before gzip

                # 2. gzip
                gz_path = tmp_path + ".gz"
                await asyncio.to_thread(self._gzip_file, tmp_path, gz_path)

                # 3. optional age encryption (compress-then-encrypt: age does
                #    not compress, and ciphertext is incompressible)
                artifact_path = gz_path
                if encryption_enabled:
                    enc_path = gz_path + ".age"
                    await self._encrypt_file(gz_path, enc_path)
                    artifact_path = enc_path

                artifact_size = os.path.getsize(artifact_path)
                checksum = await asyncio.to_thread(self._sha256_file, artifact_path)

                # 4. Upload to the primary target
                timestamp = _utcnow_naive().strftime("%Y%m%d_%H%M%S")
                suffix = ARTIFACT_SUFFIX_ENCRYPTED if enc_path else ARTIFACT_SUFFIX
                remote_name = f"backup_{timestamp}{suffix}"
                yd_remote_path = f"{yd_folder}/{remote_name}"

                provider = await self._get_yd_provider(company_id)
                if provider is None:
                    raise RuntimeError(
                        "Yandex Disk provider not available for company_id=%s"
                        % company_id
                    )

                await provider.save_file(artifact_path, yd_remote_path)

                # 5. Secondary, independent off-site copy (3-2-1 rule)
                target = "primary"
                secondary_path: str | None = None
                if secondary_enabled:
                    secondary_path = yd_remote_path
                    if await self._copy_to_secondary(artifact_path, secondary_path):
                        target = "primary+secondary"
                    else:
                        # The backup itself is intact; the redundancy is not.
                        # Counted separately so an alert can fire on it.
                        record_failure(backup_type, "secondary")
                        log.warning(
                            "backup_secondary_failed",
                            path=secondary_path,
                        )

                duration = int(time.monotonic() - started_monotonic)

                # 6. Update record
                rec = await session.get(BackupHistory, record_id)
                if rec:
                    rec.finished_at = _utcnow_naive()
                    rec.status = "success"
                    rec.size_bytes = artifact_size
                    rec.checksum = checksum
                    rec.yd_path = yd_remote_path
                    rec.secondary_path = secondary_path
                    rec.target = target
                    rec.encrypted = enc_path is not None
                    rec.duration_seconds = duration
                    await session.commit()

                record_success(backup_type, "primary", artifact_size, duration)
                if target == "primary+secondary":
                    record_success(backup_type, "secondary", artifact_size, duration)

                log.info(
                    "backup_completed",
                    size_bytes=artifact_size,
                    yd_path=yd_remote_path,
                    target=target,
                    encrypted=enc_path is not None,
                    duration_seconds=duration,
                )

                # 7. Dead-man's-switch: proves the job ran even if this host
                #    later disappears and stops exporting metrics.
                await send_heartbeat("success", detail=remote_name)

            except Exception as exc:
                duration = int(time.monotonic() - started_monotonic)
                log.error("backup_failed", error=str(exc), exc_info=True)
                rec = await session.get(BackupHistory, record_id)
                if rec:
                    rec.finished_at = _utcnow_naive()
                    rec.status = "failed"
                    rec.error_message = str(exc)[:1000]
                    rec.duration_seconds = duration
                    await session.commit()
                record_failure(backup_type, "primary")
                await send_heartbeat("fail", detail=str(exc)[:200])

            finally:
                # Clean up temp files
                for path in (tmp_path, gz_path, enc_path):
                    if path and os.path.exists(path):
                        os.remove(path)

            # 8. Rotate old backups
            try:
                await self._rotate_backups(company_id, yd_folder)
            except Exception as exc:
                log.warning("backup_rotation_failed", error=str(exc))

            result = await session.get(BackupHistory, record_id)
            return result  # type: ignore[return-value]
        finally:
            if owns_session:
                await session.close()

    async def list_backups(
        self,
        session: AsyncSession,
        limit: int = 20,
        offset: int = 0,
        company_ids: set[int] | None = None,
        backup_type: str | None = None,
    ) -> list[BackupHistory]:
        """Return recent backup records ordered by newest first."""
        stmt = (
            select(BackupHistory)
            .order_by(BackupHistory.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if company_ids is not None:
            stmt = stmt.where(BackupHistory.company_id.in_(company_ids))
        if backup_type is not None:
            stmt = stmt.where(BackupHistory.backup_type == backup_type)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_last_status(
        self,
        session: AsyncSession,
        company_ids: set[int] | None = None,
        backup_type: str | None = None,
    ) -> BackupHistory | None:
        """Return the most recent backup record."""
        stmt = (
            select(BackupHistory)
            .order_by(BackupHistory.started_at.desc())
            .limit(1)
        )
        if company_ids is not None:
            stmt = stmt.where(BackupHistory.company_id.in_(company_ids))
        if backup_type is not None:
            stmt = stmt.where(BackupHistory.backup_type == backup_type)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_backup(
        self,
        session: AsyncSession,
        backup_id: int,
        company_ids: set[int] | None = None,
    ) -> bool:
        """Delete a backup record and every remote copy of its artifact."""
        record = await session.get(BackupHistory, backup_id)
        if not record:
            return False

        if company_ids is not None and record.company_id not in company_ids:
            return False

        # Try deleting from YD if we know the path and company
        if record.yd_path and record.company_id:
            try:
                provider = await self._get_yd_provider(record.company_id)
                if provider:
                    await provider.delete_file(record.yd_path)
            except Exception as exc:
                logger.warning(
                    "backup_yd_delete_failed",
                    backup_id=backup_id,
                    error=str(exc),
                )

        secondary_path = getattr(record, "secondary_path", None)
        if secondary_path:
            try:
                await self._delete_from_secondary(secondary_path)
            except Exception as exc:
                logger.warning(
                    "backup_secondary_delete_failed",
                    backup_id=backup_id,
                    error=str(exc),
                )

        await session.delete(record)
        await session.commit()
        return True

    async def download_backup(self, backup_id: int, dest_path: str) -> str:
        """Download a stored artifact to *dest_path* and return that path.

        Shared by integrity verification and the restore drill so that both
        exercise exactly the same retrieval path a real recovery would use.
        """
        async with AsyncSessionLocal() as session:
            record = await session.get(BackupHistory, backup_id)
            if not record or not record.yd_path or not record.company_id:
                raise RuntimeError(f"Backup {backup_id} has no downloadable artifact")

            provider = await self._get_yd_provider(record.company_id)
            if not provider:
                raise RuntimeError(
                    f"Storage provider unavailable for backup {backup_id}"
                )

            await provider.save_file(record.yd_path, dest_path)
        return dest_path

    async def verify_backup_integrity(self, backup_id: int) -> bool:
        """Verify backup file checksum matches stored checksum.

        Records the outcome on the row (``verified_at`` / ``verification_status``)
        and in Prometheus, so "the last backup was never verified" is a visible
        state rather than an absence of information.

        Returns True if checksum matches, False otherwise.
        """
        async with AsyncSessionLocal() as session:
            record = await session.get(BackupHistory, backup_id)
            if (
                not record
                or not record.checksum
                or not record.yd_path
                or not record.company_id
            ):
                return False

            backup_type = getattr(record, "backup_type", "db") or "db"
            suffix = (
                ARTIFACT_SUFFIX_ENCRYPTED
                if getattr(record, "encrypted", False)
                else ARTIFACT_SUFFIX
            )

            tmp_path: str | None = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp_path = tmp.name

                await self.download_backup(backup_id, tmp_path)
                computed = await asyncio.to_thread(self._sha256_file, tmp_path)
                ok = computed == record.checksum

                record.verified_at = _utcnow_naive()
                record.verification_status = "ok" if ok else "checksum_mismatch"
                await session.commit()
                record_verification(backup_type, ok)

                if not ok:
                    logger.error(
                        "backup_checksum_mismatch",
                        backup_id=backup_id,
                        expected=record.checksum,
                        actual=computed,
                    )
                return ok
            except Exception as exc:
                logger.error(
                    "backup_verify_failed", backup_id=backup_id, error=str(exc)
                )
                try:
                    record.verification_status = "error"
                    await session.commit()
                except Exception:  # noqa: BLE001 - best effort bookkeeping
                    await session.rollback()
                record_verification(backup_type, False)
                return False
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _run_pg_dump(self) -> str:
        """Run ``pg_dump`` and return the path to the resulting dump file.

        Uses the custom archive format (``-Fc``) so that the artifact can be
        validated with ``pg_restore --list`` and restored selectively or in
        parallel.

        Includes a timeout to prevent hanging indefinitely if the
        database is unresponsive.
        """
        params = _parse_database_url(settings.DATABASE_URL)

        tmp = tempfile.NamedTemporaryFile(suffix=".dump", delete=False)
        tmp_path = tmp.name
        tmp.close()

        env = os.environ.copy()
        env["PGPASSWORD"] = params["password"]

        cmd = [
            "pg_dump",
            "-h", params["host"],
            "-p", params["port"],
            "-U", params["user"],
            "-d", params["dbname"],
            "-F", "c",            # custom format: pg_restore-able
            "-Z", "0",            # compression is handled by gzip in run_backup
            "-f", tmp_path,
        ]

        logger.info("pg_dump_started", host=params["host"], db=params["dbname"])

        process = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            _, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.PG_DUMP_TIMEOUT,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise RuntimeError(
                f"pg_dump timed out after {self.PG_DUMP_TIMEOUT}s"
            )

        if process.returncode != 0:
            error_msg = stderr.decode(errors="replace")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise RuntimeError(f"pg_dump exited with code {process.returncode}: {error_msg}")

        logger.info("pg_dump_completed", file=tmp_path, size=os.path.getsize(tmp_path))
        return tmp_path

    @staticmethod
    def _gzip_file(src: str, dst: str) -> None:
        """Compress *src* into *dst* using gzip."""
        with open(src, "rb") as f_in, gzip.open(dst, "wb", compresslevel=6) as f_out:
            while chunk := f_in.read(1024 * 1024):
                f_out.write(chunk)

    @staticmethod
    def _sha256_file(path: str) -> str:
        """Return SHA-256 hex digest of *path*."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _app_commit() -> str | None:
        """Return the deployed application revision, if it can be determined.

        Recorded alongside every backup so that a restore can be performed
        against a schema-compatible revision of the code.
        """
        env_commit = (os.environ.get("APP_COMMIT") or "").strip()
        if env_commit:
            return env_commit[:40]

        repo_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short=12", "HEAD"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except Exception:  # noqa: BLE001 - metadata only, never fatal
            return None

        if result.returncode != 0:
            return None
        return (result.stdout or "").strip()[:40] or None

    @staticmethod
    async def _run_command(cmd: list[str], label: str, timeout: int) -> None:
        """Run an external command, raising ``RuntimeError`` on failure."""
        await run_command(cmd, label=label, timeout=timeout)

    async def _encrypt_file(self, src: str, dst: str) -> None:
        """Encrypt *src* to *dst* using ``age`` with an X25519 recipient."""
        recipient = (getattr(settings, "BACKUP_AGE_RECIPIENT", "") or "").strip()
        if not recipient:
            raise RuntimeError("BACKUP_AGE_RECIPIENT is not configured")

        binary = getattr(settings, "BACKUP_AGE_BINARY", "age") or "age"
        cmd = [binary, "--encrypt", "--recipient", recipient, "--output", dst, src]
        await self._run_command(cmd, "age", timeout=self.COPY_TIMEOUT)

    async def _copy_to_secondary(self, src: str, remote_path: str) -> bool:
        """Push *src* to the secondary remote. Returns True on success."""
        remote = (
            getattr(settings, "BACKUP_SECONDARY_RCLONE_REMOTE", "") or ""
        ).strip()
        if not remote:
            return False

        binary = getattr(settings, "BACKUP_RCLONE_BINARY", "rclone") or "rclone"
        target = f"{remote.rstrip('/')}/{remote_path.lstrip('/')}"
        try:
            await self._run_command(
                [binary, "copyto", src, target],
                "rclone",
                timeout=self.COPY_TIMEOUT,
            )
        except Exception as exc:  # noqa: BLE001 - primary copy already exists
            logger.warning("backup_secondary_copy_failed", error=str(exc))
            return False
        return True

    async def _delete_from_secondary(self, remote_path: str) -> None:
        """Remove a single artifact from the secondary remote."""
        remote = (
            getattr(settings, "BACKUP_SECONDARY_RCLONE_REMOTE", "") or ""
        ).strip()
        if not remote:
            return

        binary = getattr(settings, "BACKUP_RCLONE_BINARY", "rclone") or "rclone"
        target = f"{remote.rstrip('/')}/{remote_path.lstrip('/')}"
        await self._run_command(
            [binary, "deletefile", target], "rclone", timeout=self.PG_DUMP_TIMEOUT
        )

    @staticmethod
    async def _get_yd_provider(
        company_id: int,
    ) -> YandexDiskStorageProvider | None:
        """Resolve the Yandex Disk provider for *company_id*."""
        async with AsyncSessionLocal() as session:
            company = await session.get(Company, company_id)
            if not company:
                return None
            provider = await get_provider_for_company(company)
            if isinstance(provider, YandexDiskStorageProvider):
                return provider
            return None

    @staticmethod
    def _gfs_limits(backup_settings) -> dict[str, int] | None:
        """Return the GFS ladder when the deployment configures one.

        Deployments that predate the GFS ladder only carry ``backup_max_copies``
        / ``backup_retention_days``. Rather than inventing a ladder from
        unrelated values we fall back to the legacy rule for them, and switch
        to GFS as soon as the ladder is present.

        Returns keyword arguments ready for :func:`select_gfs_deletes`.
        """
        attr_names = (
            "backup_keep_daily",
            "backup_keep_weekly",
            "backup_keep_monthly",
            "backup_keep_yearly",
        )
        arg_names = ("keep_daily", "keep_weekly", "keep_monthly", "keep_yearly")

        values = [getattr(backup_settings, name, None) for name in attr_names]
        if all(value is None for value in values):
            return None

        defaults = (
            getattr(settings, "BACKUP_KEEP_DAILY", DEFAULT_KEEP_DAILY),
            getattr(settings, "BACKUP_KEEP_WEEKLY", DEFAULT_KEEP_WEEKLY),
            getattr(settings, "BACKUP_KEEP_MONTHLY", DEFAULT_KEEP_MONTHLY),
            getattr(settings, "BACKUP_KEEP_YEARLY", DEFAULT_KEEP_YEARLY),
        )
        return {
            arg: int(value if value is not None else default)
            for arg, value, default in zip(arg_names, values, defaults)
        }

    async def _rotate_backups(
        self,
        company_id: int,
        yd_folder: str,
    ) -> None:
        """Remove backups that exceed the retention ladder.

        Uses the GFS ladder (7 daily / 4 weekly / 12 monthly / 3 yearly) when
        configured, otherwise the legacy ``max_copies`` + ``retention_days``
        rule. Files are removed from every remote that holds a copy.
        """
        from app.services.settings_service import SettingsService

        async with AsyncSessionLocal() as session:
            svc = SettingsService(session)
            all_settings = await svc.get_all_settings()
            backup_settings = all_settings.backup
            retention_days = backup_settings.backup_retention_days
            max_copies = backup_settings.backup_max_copies
            gfs = self._gfs_limits(backup_settings)

        async with AsyncSessionLocal() as session:
            # Fetch all successful backups for this company, newest first
            stmt = (
                select(BackupHistory)
                .where(
                    BackupHistory.company_id == company_id,
                    BackupHistory.status == "success",
                )
                .order_by(BackupHistory.started_at.desc())
            )
            result = await session.execute(stmt)
            backups = list(result.scalars().all())

        if gfs is not None:
            to_delete = select_gfs_deletes(backups, **gfs)
            rule = "gfs"
        else:
            cutoff = _utcnow_naive() - timedelta(days=retention_days)
            to_delete = [
                bkp
                for idx, bkp in enumerate(backups)
                if idx >= max_copies
                or (bkp.started_at and bkp.started_at < cutoff)
            ]
            rule = "legacy"

        if not to_delete:
            return

        provider = await self._get_yd_provider(company_id)

        async with AsyncSessionLocal() as session:
            for bkp in to_delete:
                record = await session.get(BackupHistory, bkp.id)
                if not record:
                    continue
                # Delete from YD
                if record.yd_path and provider:
                    try:
                        await provider.delete_file(record.yd_path)
                    except Exception as e:
                        logger.warning("backup_rotation_yd_delete_failed", yd_path=record.yd_path, error=str(e))
                # Delete the secondary copy too, otherwise the ladder only
                # applies to one of the two off-site copies.
                secondary_path = getattr(record, "secondary_path", None)
                if secondary_path:
                    try:
                        await self._delete_from_secondary(secondary_path)
                    except Exception as e:
                        logger.warning(
                            "backup_rotation_secondary_delete_failed",
                            path=secondary_path,
                            error=str(e),
                        )
                await session.delete(record)
            await session.commit()

        logger.info("backup_rotation_done", deleted=len(to_delete), rule=rule)
