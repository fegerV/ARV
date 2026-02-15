"""Service for creating, uploading and rotating PostgreSQL backups.

The service runs ``pg_dump`` as a subprocess, compresses the output,
uploads the resulting file to Yandex Disk via the company's storage
provider, and records the operation in ``backup_history``.
"""

from __future__ import annotations

import asyncio
import gzip
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.storage_providers import get_provider_for_company
from app.core.yandex_disk_provider import YandexDiskStorageProvider
from app.models.backup import BackupHistory
from app.models.company import Company

logger = structlog.get_logger()


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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_backup(
        self,
        company_id: int,
        yd_folder: str = "backups",
        trigger: str = "manual",
    ) -> BackupHistory:
        """Execute a full backup: dump, compress, upload, record.

        Args:
            company_id: Company whose Yandex Disk token will be used.
            yd_folder: Target folder on Yandex Disk.
            trigger: ``"manual"`` or ``"scheduled"``.

        Returns:
            The ``BackupHistory`` record with the outcome.
        """
        log = logger.bind(company_id=company_id, trigger=trigger)
        log.info("backup_started")

        async with AsyncSessionLocal() as session:
            record = BackupHistory(
                started_at=datetime.utcnow(),
                status="running",
                company_id=company_id,
                trigger=trigger,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            record_id = record.id

        tmp_path: Optional[str] = None
        gz_path: Optional[str] = None

        try:
            # 1. pg_dump
            tmp_path = await self._run_pg_dump()
            file_size = os.path.getsize(tmp_path)

            # 2. gzip
            gz_path = tmp_path + ".gz"
            await asyncio.to_thread(self._gzip_file, tmp_path, gz_path)
            gz_size = os.path.getsize(gz_path)

            # 3. Upload to Yandex Disk
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            remote_name = f"backup_{timestamp}.sql.gz"
            yd_remote_path = f"{yd_folder}/{remote_name}"

            provider = await self._get_yd_provider(company_id)
            if provider is None:
                raise RuntimeError(
                    "Yandex Disk provider not available for company_id=%s"
                    % company_id
                )

            # Read in a thread to avoid blocking the event loop for large files
            data = await asyncio.to_thread(Path(gz_path).read_bytes)
            await provider.save_file_bytes(data, yd_remote_path)

            # 4. Update record
            async with AsyncSessionLocal() as session:
                rec = await session.get(BackupHistory, record_id)
                if rec:
                    rec.finished_at = datetime.utcnow()
                    rec.status = "success"
                    rec.size_bytes = gz_size
                    rec.yd_path = yd_remote_path
                    await session.commit()

            log.info(
                "backup_completed",
                size_bytes=gz_size,
                yd_path=yd_remote_path,
            )

        except Exception as exc:
            log.error("backup_failed", error=str(exc), exc_info=True)
            async with AsyncSessionLocal() as session:
                rec = await session.get(BackupHistory, record_id)
                if rec:
                    rec.finished_at = datetime.utcnow()
                    rec.status = "failed"
                    rec.error_message = str(exc)[:1000]
                    await session.commit()

        finally:
            # Clean up temp files
            for path in (tmp_path, gz_path):
                if path and os.path.exists(path):
                    os.remove(path)

        # 5. Rotate old backups
        try:
            await self._rotate_backups(company_id, yd_folder)
        except Exception as exc:
            log.warning("backup_rotation_failed", error=str(exc))

        async with AsyncSessionLocal() as session:
            result = await session.get(BackupHistory, record_id)
            return result  # type: ignore[return-value]

    async def list_backups(
        self,
        session: AsyncSession,
        limit: int = 20,
        offset: int = 0,
    ) -> list[BackupHistory]:
        """Return recent backup records ordered by newest first."""
        stmt = (
            select(BackupHistory)
            .order_by(BackupHistory.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_last_status(
        self, session: AsyncSession
    ) -> Optional[BackupHistory]:
        """Return the most recent backup record."""
        stmt = (
            select(BackupHistory)
            .order_by(BackupHistory.started_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_backup(
        self,
        session: AsyncSession,
        backup_id: int,
    ) -> bool:
        """Delete a backup record and the file on Yandex Disk."""
        record = await session.get(BackupHistory, backup_id)
        if not record:
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

        await session.delete(record)
        await session.commit()
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    # Maximum time (seconds) to wait for pg_dump before killing it.
    PG_DUMP_TIMEOUT: int = 600  # 10 minutes

    async def _run_pg_dump(self) -> str:
        """Run ``pg_dump`` and return the path to the resulting SQL file.

        Includes a timeout to prevent hanging indefinitely if the
        database is unresponsive.
        """
        params = _parse_database_url(settings.DATABASE_URL)

        tmp = tempfile.NamedTemporaryFile(suffix=".sql", delete=False)
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
            "-F", "p",            # plain-text SQL
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
    async def _get_yd_provider(
        company_id: int,
    ) -> Optional[YandexDiskStorageProvider]:
        """Resolve the Yandex Disk provider for *company_id*."""
        async with AsyncSessionLocal() as session:
            company = await session.get(Company, company_id)
            if not company:
                return None
            provider = await get_provider_for_company(company)
            if isinstance(provider, YandexDiskStorageProvider):
                return provider
            return None

    async def _rotate_backups(
        self,
        company_id: int,
        yd_folder: str,
    ) -> None:
        """Remove backups that exceed retention or max-copy limits.

        Reads current limits from the database settings.
        """
        from app.services.settings_service import SettingsService

        async with AsyncSessionLocal() as session:
            svc = SettingsService(session)
            all_settings = await svc.get_all_settings()
            retention_days = all_settings.backup.backup_retention_days
            max_copies = all_settings.backup.backup_max_copies

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

        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        to_delete: list[int] = []

        for idx, bkp in enumerate(backups):
            if idx >= max_copies or (bkp.started_at and bkp.started_at < cutoff):
                to_delete.append(bkp.id)

        if not to_delete:
            return

        provider = await self._get_yd_provider(company_id)

        async with AsyncSessionLocal() as session:
            for bkp_id in to_delete:
                record = await session.get(BackupHistory, bkp_id)
                if not record:
                    continue
                # Delete from YD
                if record.yd_path and provider:
                    try:
                        await provider.delete_file(record.yd_path)
                    except Exception:
                        pass
                await session.delete(record)
            await session.commit()

        logger.info("backup_rotation_done", deleted=len(to_delete))
