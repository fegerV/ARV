"""Restore, dump validation and restore-drill verification.

The design doc is blunt about this (``docs/BACKUP_AND_RECOVERY.md`` §7, §10):
*an unverified backup is not a backup*. The previous implementation only
compared a checksum of the uploaded file, which proves the bytes survived the
trip to the remote — not that they can be turned back into a working database.
A dump can be byte-perfect and still be unrestorable (wrong pg_dump version,
truncated mid-table, missing extension, corrupted archive index).

This service therefore provides three escalating levels of proof:

1. :meth:`RestoreService.materialize_dump` — download, decrypt and decompress a
   backup exactly the way a real recovery would, so any weakness in the
   retrieval path shows up here rather than during an incident.
2. :meth:`RestoreService.verify_dump` — ``pg_restore --list`` against the
   materialised archive. This reads the archive's own table of contents, so it
   catches truncation and format problems **without touching a server**. Cheap
   enough to run after every backup.
3. :meth:`RestoreService.restore_drill` — restore into a throwaway database on
   the real cluster and count the resulting tables. This is the only test that
   proves the data is actually usable, and it is the basis of the monthly
   drill and the ``arv_backup_restore_drill_last_timestamp_seconds`` metric.

Nothing here is invoked on the request path: restores are operator-initiated
(``restore_to``) or timer-driven (``restore_drill``).
"""

from __future__ import annotations

import asyncio
import gzip
import os
import re
import shutil
import tempfile
import time
from datetime import datetime, UTC

import structlog

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.backup import BackupHistory
from app.services.backup_metrics import record_restore_drill
from app.services.backup_service import (
    ARTIFACT_SUFFIX,
    BackupService,
    _parse_database_url,
    _utcnow_naive,
)
from app.utils.command import CommandError, binary_available, run_command

logger = structlog.get_logger()

# A drill database name is interpolated into SQL, so it must be provably safe.
_IDENTIFIER_RE = re.compile(r"^[a-z_][a-z0-9_]{0,50}$")

# ``verification_status`` / ``restore_test_status`` values persisted on the row.
STATUS_OK = "ok"
STATUS_LIST_FAILED = "list_failed"
STATUS_RESTORE_FAILED = "restore_failed"
# The artifact is encrypted and the age identity is, by design, not present on
# this host (docs/BACKUP_AND_RECOVERY.md, "Encryption": the key must not live on
# the production server). The archive therefore cannot be opened here. This is
# deliberately NOT a failure status: nothing is wrong with the backup — the
# operator has simply not mounted the key. Reporting it as a failure would make
# the weekly verify and monthly drill alarm forever, and a permanently red
# safety net is worse than none: it trains operators to ignore the alert that
# is supposed to catch a genuinely corrupt backup.
STATUS_NO_IDENTITY = "no_identity"


class ArtifactUnavailable(RuntimeError):
    """The backup has no single file to hand out.

    Raised for media backups: those are ``restic`` snapshots (a repository of
    deduplicated chunks), not one artifact, so "download the file" has no
    meaning for them. The API turns this into a 409 with the reason attached
    rather than a 500, because the request is understood and simply does not
    apply.
    """


class DecryptionUnavailable(RuntimeError):
    """The artifact is encrypted and this host has no age identity.

    Not an error in the backup — the key is deliberately kept off the
    production host (docs/BACKUP_AND_RECOVERY.md, "Encryption"). The operator
    either downloads the artifact as-is and decrypts it where the key lives, or
    mounts the key and retries.
    """


class RestoreService:
    """Retrieve, validate and restore database backups."""

    DECRYPT_TIMEOUT: int = 3600
    RESTORE_TIMEOUT: int = 3600
    LIST_TIMEOUT: int = 600

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    async def materialize_dump(self, backup_id: int, workdir: str) -> str:
        """Download, decrypt and decompress backup *backup_id*.

        Returns the path to a readable custom-format ``.dump`` file inside
        *workdir*. The caller owns *workdir* and is responsible for removing it.
        """
        os.makedirs(workdir, exist_ok=True)

        encrypted, artifact_name = await self._artifact_metadata(backup_id)
        if not artifact_name:
            artifact_name = f"backup_{backup_id}{ARTIFACT_SUFFIX}"
        artifact_path = os.path.join(workdir, artifact_name)

        await BackupService().download_backup(backup_id, artifact_path)

        # 1. decrypt (age) when the artifact was encrypted before upload
        if encrypted:
            gz_path = (
                artifact_path[: -len(".age")]
                if artifact_path.endswith(".age")
                else artifact_path + ".gz"
            )
            await self._decrypt_file(artifact_path, gz_path)
        else:
            gz_path = artifact_path

        # 2. decompress (gzip) -> the custom-format archive pg_restore reads.
        #    Named deterministically: the stored artifact keeps a .sql.gz name
        #    for backward compatibility, which would otherwise yield a
        #    custom-format archive misleadingly called ".sql".
        dump_path = os.path.join(workdir, f"backup_{backup_id}.dump")
        await asyncio.to_thread(self._gunzip_file, gz_path, dump_path)

        if not os.path.exists(dump_path) or os.path.getsize(dump_path) == 0:
            raise RuntimeError(f"Materialised dump for backup {backup_id} is empty")

        return dump_path

    async def fetch_artifact(
        self,
        backup_id: int,
        workdir: str,
        *,
        decrypt: bool = False,
    ) -> dict:
        """Materialise backup *backup_id* as a single downloadable file.

        This is the manual-download path. It deliberately stops one step
        earlier than :meth:`materialize_dump`: the operator receives the
        artifact exactly as it was stored — still gzipped, still
        ``age``-encrypted. That is usually what is wanted, because the reason
        to pull a backup by hand is to carry it somewhere the production host
        cannot reach, and the encrypted artifact is the only form that is safe
        to carry.

        ``decrypt=True`` opens it in place, but only when the age identity is
        present on this host; otherwise :class:`DecryptionUnavailable` is
        raised rather than quietly returning the encrypted bytes under a name
        that implies otherwise.

        The caller owns *workdir* and must remove it.
        """
        os.makedirs(workdir, exist_ok=True)

        async with AsyncSessionLocal() as session:
            record = await session.get(BackupHistory, backup_id)
            if record is None:
                raise RuntimeError(f"Backup {backup_id} not found")
            backup_type = getattr(record, "backup_type", "db") or "db"
            yd_path = (record.yd_path or "").strip()
            encrypted = bool(getattr(record, "encrypted", False))

        if backup_type == "media":
            raise ArtifactUnavailable(
                "Media backups are restic snapshots, not a single file. "
                "Restore them with `restic restore <snapshot> --target ...` "
                "(docs/RESTORE_RUNBOOK.md §7)."
            )
        if not yd_path:
            raise ArtifactUnavailable(f"Backup {backup_id} has no stored artifact path.")

        filename = os.path.basename(yd_path) or f"backup_{backup_id}"
        dest = os.path.join(workdir, filename)

        # One column carries two storage shapes: db artifacts are relative
        # paths on Yandex Disk, secrets archives are absolute paths inside the
        # local staging directory (they are never uploaded when no secondary
        # target is configured). Absolute-and-present therefore means local.
        if os.path.isabs(yd_path) and os.path.exists(yd_path):
            await asyncio.to_thread(shutil.copyfile, yd_path, dest)
            os.chmod(dest, 0o600)
        else:
            await BackupService().download_backup(backup_id, dest)

        # ``plaintext`` describes the file being returned, ``encrypted`` the
        # file as stored. They differ exactly when the caller asked for and
        # received a decrypted artifact.
        plaintext = not encrypted
        if decrypt and encrypted:
            if not self.decryption_possible(True):
                raise DecryptionUnavailable(
                    "Backup is encrypted and BACKUP_AGE_IDENTITY_FILE is not "
                    "available on this host. Download it as-is and decrypt it "
                    "where the key lives, or mount the key and retry."
                )
            opened = dest[: -len(".age")] if dest.endswith(".age") else dest + ".plain"
            await self._decrypt_file(dest, opened)
            os.remove(dest)
            dest = opened
            filename = os.path.basename(dest)
            plaintext = True

        return {
            "path": dest,
            "filename": filename,
            "encrypted": encrypted,
            "plaintext": plaintext,
            "size_bytes": os.path.getsize(dest),
            "backup_type": backup_type,
        }

    @staticmethod
    async def _artifact_metadata(backup_id: int) -> tuple[bool, str | None]:
        """Return ``(encrypted, basename)`` for a backup row."""
        async with AsyncSessionLocal() as session:
            record = await session.get(BackupHistory, backup_id)
            if record is None:
                raise RuntimeError(f"Backup {backup_id} not found")

            encrypted = bool(getattr(record, "encrypted", False))
            basename = None
            if record.yd_path:
                basename = os.path.basename(record.yd_path)
            return encrypted, basename

    @staticmethod
    def decryption_possible(encrypted: bool) -> bool:
        """True when this host is able to open an encrypted artifact.

        Plain dumps are always readable. Encrypted ones need the ``age``
        identity, which is deliberately kept off the production host, so
        outside a restore window the expected answer is ``False``.
        """
        if not encrypted:
            return True
        identity = (getattr(settings, "BACKUP_AGE_IDENTITY_FILE", "") or "").strip()
        return bool(identity) and os.path.exists(identity)

    async def _skip_without_identity(self, backup_id: int) -> dict | None:
        """Return a skip report when *backup_id* is encrypted and unopenable.

        ``None`` means the caller may proceed normally.
        """
        encrypted, _ = await self._artifact_metadata(backup_id)
        if self.decryption_possible(encrypted):
            return None
        return {
            "ok": False,
            "skipped": True,
            "reason": (
                "backup is encrypted and BACKUP_AGE_IDENTITY_FILE is not "
                "available on this host; mount the age identity to verify it"
            ),
        }

    async def _decrypt_file(self, src: str, dst: str) -> None:
        """Decrypt *src* into *dst* with ``age`` using the restore identity."""
        identity = (
            getattr(settings, "BACKUP_AGE_IDENTITY_FILE", "") or ""
        ).strip()
        if not identity:
            raise RuntimeError(
                "BACKUP_AGE_IDENTITY_FILE is not configured; the encrypted "
                "backup cannot be decrypted on this host"
            )
        if not os.path.exists(identity):
            raise RuntimeError(f"age identity file not found: {identity}")

        binary = (getattr(settings, "BACKUP_AGE_BINARY", "age") or "age").strip()
        await run_command(
            [binary, "--decrypt", "--identity", identity, "--output", dst, src],
            label="age --decrypt",
            timeout=self.DECRYPT_TIMEOUT,
        )

    @staticmethod
    def _gunzip_file(src: str, dst: str) -> None:
        """Stream-decompress *src* into *dst*."""
        with gzip.open(src, "rb") as f_in, open(dst, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out, length=1024 * 1024)

    # ------------------------------------------------------------------
    # Level 2: archive validation without a server
    # ------------------------------------------------------------------

    async def verify_dump(self, backup_id: int) -> dict:
        """Validate a backup archive with ``pg_restore --list``.

        Returns a report dict; also records ``verified_at`` /
        ``verification_status`` on the backup row.
        """
        binary = (
            getattr(settings, "BACKUP_PG_RESTORE_BINARY", "pg_restore") or "pg_restore"
        ).strip()
        if not binary_available(binary):
            return {"ok": False, "error": f"{binary} not found on PATH"}

        skip = await self._skip_without_identity(backup_id)
        if skip is not None:
            await self._record_verification(backup_id, STATUS_NO_IDENTITY)
            logger.info(
                "backup_dump_verify_skipped",
                backup_id=backup_id,
                reason=skip["reason"],
            )
            return skip

        workdir = tempfile.mkdtemp(prefix="arv-verify-")
        try:
            dump_path = await self.materialize_dump(backup_id, workdir)
            listing = await run_command(
                [binary, "--list", dump_path],
                label="pg_restore --list",
                timeout=self.LIST_TIMEOUT,
                capture_stdout=True,
            )

            entries = [
                line
                for line in listing.splitlines()
                if line and not line.startswith(";")
            ]
            tables = [
                line
                for line in entries
                if re.search(r"\sTABLE\s", line) or " TABLE DATA " in line
            ]

            report = {
                "ok": bool(entries),
                "entries": len(entries),
                "tables": len(tables),
            }
            await self._record_verification(
                backup_id,
                STATUS_OK if report["ok"] else STATUS_LIST_FAILED,
            )
            logger.info("backup_dump_verified", backup_id=backup_id, **report)
            return report
        except Exception as exc:
            logger.error("backup_dump_verify_failed", backup_id=backup_id, error=str(exc))
            await self._record_verification(backup_id, STATUS_LIST_FAILED)
            return {"ok": False, "error": str(exc)}
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Level 3: restore drill / real restore
    # ------------------------------------------------------------------

    async def restore_drill(self, backup_id: int) -> dict:
        """Restore *backup_id* into a throwaway database and verify it.

        This is the monthly automated proof that the backup is usable. The
        throwaway database is dropped in a ``finally`` block, so a failed drill
        never leaves debris behind.

        An encrypted backup cannot be drilled while the age identity is off the
        host. That case returns ``skipped`` and is recorded as
        ``no_identity`` — deliberately not as a failure, and deliberately
        without touching the drill metric, so the "drill overdue" alert keeps
        telling the truth (no drill has actually proved the backup usable)
        instead of firing a false "drill failed" every month.
        """
        skip = await self._skip_without_identity(backup_id)
        if skip is not None:
            await self._record_drill(backup_id, STATUS_NO_IDENTITY)
            logger.info(
                "backup_restore_drill_skipped",
                backup_id=backup_id,
                reason=skip["reason"],
            )
            return skip

        drill_db = self._drill_db_name()
        started = time.monotonic()

        workdir = tempfile.mkdtemp(prefix="arv-drill-")
        try:
            dump_path = await self.materialize_dump(backup_id, workdir)
            await self._create_database(drill_db)
            try:
                await self._pg_restore_into(drill_db, dump_path)
                table_count = await self._count_tables(drill_db)
            finally:
                await self._drop_database(drill_db)

            duration = int(time.monotonic() - started)
            ok = table_count > 0
            report = {
                "ok": ok,
                "tables_restored": table_count,
                "duration_seconds": duration,
                "drill_database": drill_db,
            }
            await self._record_drill(backup_id, STATUS_OK if ok else STATUS_RESTORE_FAILED)
            record_restore_drill(ok)
            logger.info("backup_restore_drill_completed", backup_id=backup_id, **report)
            return report
        except Exception as exc:
            logger.error(
                "backup_restore_drill_failed", backup_id=backup_id, error=str(exc)
            )
            await self._record_drill(backup_id, STATUS_RESTORE_FAILED)
            record_restore_drill(False)
            return {"ok": False, "error": str(exc)}
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    async def restore_to(
        self,
        backup_id: int,
        target_db: str,
        *,
        create_if_missing: bool = False,
    ) -> dict:
        """Restore *backup_id* into *target_db* (operator-initiated recovery).

        Refuses to run against the configured application database: restoring
        over live production data is the classic way an incident becomes worse,
        and the runbook (§10.1, step 0) requires the application to be stopped
        and the current state preserved first.

        ``create_if_missing`` creates the target database when it is absent.
        That removes the ``createdb`` step which previously had to happen by
        hand before every restore — the single most common way the documented
        procedure stalled. It is opt-in because the two callers want opposite
        things: a drill must own the database it later drops, while an operator
        restore must not silently conjure a database they did not mean to
        target.
        """
        if not _IDENTIFIER_RE.match(target_db or ""):
            raise ValueError(f"Unsafe target database name: {target_db!r}")

        live_db = _parse_database_url(settings.DATABASE_URL)["dbname"]
        if target_db == live_db:
            raise RuntimeError(
                f"Refusing to restore over the live database {live_db!r}. "
                "Restore into a separate database and cut over deliberately."
            )

        started = time.monotonic()
        workdir = tempfile.mkdtemp(prefix="arv-restore-")
        created = False
        try:
            dump_path = await self.materialize_dump(backup_id, workdir)
            if create_if_missing and not await self._database_exists(target_db):
                await self._create_database(target_db)
                created = True
                logger.info("restore_target_created", target_database=target_db)
            await self._pg_restore_into(target_db, dump_path)
            table_count = await self._count_tables(target_db)
            report = {
                "ok": True,
                "tables_restored": table_count,
                "target_database": target_db,
                "created_database": created,
                "duration_seconds": int(time.monotonic() - started),
            }
            logger.info("backup_restore_completed", backup_id=backup_id, **report)
            return report
        except Exception as exc:
            logger.error("backup_restore_failed", backup_id=backup_id, error=str(exc))
            return {"ok": False, "error": str(exc), "target_database": target_db}
        finally:
            # A failed restore deliberately leaves a created database behind
            # rather than dropping it: a half-restored database is evidence,
            # and the operator can inspect or drop it explicitly.
            shutil.rmtree(workdir, ignore_errors=True)

    # ------------------------------------------------------------------
    # PostgreSQL helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _params() -> dict:
        return _parse_database_url(settings.DATABASE_URL)

    @staticmethod
    def _pg_env() -> dict[str, str]:
        return {"PGPASSWORD": RestoreService._params()["password"]}

    def _psql_base(self, database: str) -> list[str]:
        binary = (getattr(settings, "BACKUP_PSQL_BINARY", "psql") or "psql").strip()
        params = self._params()
        return [
            binary,
            "-h", params["host"],
            "-p", params["port"],
            "-U", params["user"],
            "-d", database,
            "-v", "ON_ERROR_STOP=1",
            "-tA",
        ]

    async def _psql(self, sql: str, database: str) -> str:
        """Run a single SQL statement and return trimmed stdout."""
        stdout = await run_command(
            [*self._psql_base(database), "-c", sql],
            label="psql",
            timeout=self.LIST_TIMEOUT,
            env=self._pg_env(),
            capture_stdout=True,
        )
        return stdout.strip()

    async def _database_exists(self, name: str) -> bool:
        """True when *name* is already a database on this cluster."""
        if not _IDENTIFIER_RE.match(name):
            return False
        raw = await self._psql(
            f"SELECT 1 FROM pg_database WHERE datname = '{name}'", "postgres"
        )
        return raw.strip() == "1"

    async def _create_database(self, name: str) -> None:
        if not _IDENTIFIER_RE.match(name):
            raise ValueError(f"Unsafe database name: {name!r}")
        await self._psql(f'CREATE DATABASE "{name}"', "postgres")

    async def _drop_database(self, name: str) -> None:
        if not _IDENTIFIER_RE.match(name):
            return
        try:
            await self._psql(f'DROP DATABASE IF EXISTS "{name}"', "postgres")
        except CommandError as exc:
            logger.warning("restore_drill_drop_failed", database=name, error=str(exc))

    async def _count_tables(self, database: str) -> int:
        raw = await self._psql(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = 'public'",
            database,
        )
        try:
            return int(raw)
        except (TypeError, ValueError):
            return 0

    async def _pg_restore_into(self, database: str, dump_path: str) -> None:
        """Restore *dump_path* into *database*.

        ``--exit-on-error`` is intentional: a drill that silently tolerates
        errors proves nothing. ``-j`` works because the dump uses the custom
        format.

        ``--no-owner`` is required, not cosmetic. A dump records each object's
        owner, and pg_restore replays that as ``ALTER ... OWNER TO <role>``,
        which needs the restoring role to be able to ``SET ROLE`` to it. The
        production cluster has five objects owned by ``postgres`` (``ai_jobs``
        and its sequence/indexes, created by an early migration run as a
        superuser) while the application connects as ``vertex_ar`` — so the
        replay aborted on ``ALTER TABLE public.ai_jobs OWNER TO postgres`` and,
        with ``--exit-on-error``, took the whole restore with it, leaving the
        target database empty. Restoring into a *separate* database and cutting
        over deliberately is the documented model, so ownership is expected to
        be re-established by the restoring role anyway.
        """
        binary = (
            getattr(settings, "BACKUP_PG_RESTORE_BINARY", "pg_restore") or "pg_restore"
        ).strip()
        jobs = max(1, int(getattr(settings, "BACKUP_RESTORE_JOBS", 4)))
        params = self._params()

        await run_command(
            [
                binary,
                "-h", params["host"],
                "-p", params["port"],
                "-U", params["user"],
                "-d", database,
                "-j", str(jobs),
                "--no-owner",
                "--exit-on-error",
                dump_path,
            ],
            label="pg_restore",
            timeout=self.RESTORE_TIMEOUT,
            env=self._pg_env(),
        )

    # ------------------------------------------------------------------
    # Bookkeeping
    # ------------------------------------------------------------------

    @staticmethod
    def _drill_db_name() -> str:
        prefix = (
            getattr(settings, "BACKUP_DRILL_DB_PREFIX", "arv_drill") or "arv_drill"
        ).strip().lower()
        if not _IDENTIFIER_RE.match(prefix):
            prefix = "arv_drill"
        return f"{prefix}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

    @staticmethod
    async def _record_verification(backup_id: int, status: str) -> None:
        async with AsyncSessionLocal() as session:
            record = await session.get(BackupHistory, backup_id)
            if record is None:
                return
            record.verified_at = _utcnow_naive()
            record.verification_status = status
            await session.commit()

    @staticmethod
    async def _record_drill(backup_id: int, status: str) -> None:
        async with AsyncSessionLocal() as session:
            record = await session.get(BackupHistory, backup_id)
            if record is None:
                return
            record.restore_tested_at = _utcnow_naive()
            record.restore_test_status = status
            await session.commit()
