"""APScheduler integration for periodic database backups.

The scheduler is started during application startup and reads its
configuration from the ``backup`` section of system settings.  When
backup settings are changed via the admin panel the schedule is
re-applied at runtime without restarting the application.
"""

from __future__ import annotations

import os

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.database import AsyncSessionLocal
from app.services.settings_service import SettingsService

try:  # POSIX only. Production is Linux; the test suite also runs on Windows.
    import fcntl
except ImportError:  # pragma: no cover - exercised on Windows only
    fcntl = None  # type: ignore[assignment]

logger = structlog.get_logger()

_JOB_ID = "db_backup"

# Deliberately the same file ``deploy/backup/backup-db.sh`` locks via
# ``acquire_lock "db"``. Sharing it means the in-app scheduler and the systemd
# timer are mutually safe: whichever gets there first runs the backup and the
# other skips, instead of both dumping the database.
#
# ``ARV_BACKUP_LOCK_DIR`` is honoured too, because that is the variable
# ``deploy/backup/common.sh`` uses. If an operator relocates the lock directory
# for the shell scripts, the scheduler has to follow, or the two would lock
# different files and the mutual exclusion would quietly stop working.
# ``ARV_BACKUP_LOCK_PATH`` overrides both when a full path is wanted.
DEFAULT_LOCK_PATH = "/var/lock/arv-db.lock"


def _resolve_lock_path(env) -> str:
    """Work out which file to lock, mirroring ``deploy/backup/common.sh``."""
    explicit = env.get("ARV_BACKUP_LOCK_PATH")
    if explicit:
        return explicit
    lock_dir = env.get("ARV_BACKUP_LOCK_DIR")
    if lock_dir:
        return os.path.join(lock_dir, "arv-db.lock")
    return DEFAULT_LOCK_PATH


JOB_LOCK_PATH = _resolve_lock_path(os.environ)

scheduler = AsyncIOScheduler()


class JobLock:
    """Cross-process guard so exactly one worker runs the backup.

    gunicorn runs several workers and each one starts its own APScheduler
    during lifespan, so without this every worker fires the same cron job in
    the same second. That is not merely wasteful — it corrupts the backup:

    * the artifact name is derived from a timestamp with one-second
      granularity, so the duplicates compute the *same* remote path and upload
      to the same key;
    * each run still writes its own ``backup_history`` row, so two rows end up
      pointing at one artifact;
    * rotation then sees two backups for the same day, deletes the older row,
      and removes the artifact with it — leaving the surviving row marked
      ``success`` while its file is gone.

    Observed in production on 2026-09-16: backup 150 was ``success`` and its
    artifact returned 404 from Yandex Disk.

    ``flock`` is used rather than an in-process flag because the contention is
    between processes, and because the kernel releases the lock if the holder
    dies mid-run. Where the primitive is unavailable (Windows) it degrades to
    "always run", which is correct for single-process environments.

    The failure direction is deliberate: this guard only ever *prevents a
    duplicate*. If the lock file cannot even be opened it reports success and
    lets the backup run, because silently skipping would stop backups entirely
    — the one outcome worse than a duplicate.
    """

    def __init__(self, path: str):
        self.path = path
        self._handle = None

    def acquire(self) -> bool:
        if fcntl is None:
            return True
        try:
            parent = os.path.dirname(self.path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            self._handle = open(self.path, "w")
        except OSError as exc:
            # The lock file itself is unusable — the directory is missing or
            # not writable. Skipping would silently stop backups altogether, so
            # run anyway: a duplicate backup is recoverable, a missing one is
            # not. This is why a broken lock must not be conflated with
            # contention below.
            logger.warning("backup_lock_unavailable", path=self.path, error=str(exc))
            self.release()
            return True
        try:
            fcntl.flock(self._handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            # Someone else holds it — the expected duplicate case.
            self.release()
            return False
        return True

    def release(self) -> None:
        if self._handle is None:
            return
        try:
            if fcntl is not None:
                fcntl.flock(self._handle, fcntl.LOCK_UN)
        finally:
            self._handle.close()
            self._handle = None


async def _scheduled_backup_job() -> None:
    """Entry-point executed by APScheduler on each trigger."""
    logger.info("scheduled_backup_triggered")

    lock = JobLock(JOB_LOCK_PATH)
    if not lock.acquire():
        logger.info(
            "scheduled_backup_skipped", reason="another_process_is_running_it"
        )
        return

    try:
        await _run_scheduled_backup()
    finally:
        lock.release()


async def _run_scheduled_backup() -> None:
    async with AsyncSessionLocal() as session:
        svc = SettingsService(session)
        all_settings = await svc.get_all_settings()

    bkp = all_settings.backup
    if not bkp.backup_enabled or not bkp.backup_company_id:
        logger.info("scheduled_backup_skipped", reason="disabled_or_no_company")
        return

    from app.services.backup_service import BackupService

    service = BackupService()
    async with AsyncSessionLocal() as session:
        await service.run_backup(
            session=session,
            company_id=bkp.backup_company_id,
            yd_folder=bkp.backup_yd_folder,
            trigger="scheduled",
        )


async def init_scheduler() -> None:
    """Load backup settings from DB and start the scheduler.

    Called once during application startup inside the lifespan handler.
    """
    try:
        async with AsyncSessionLocal() as session:
            svc = SettingsService(session)
            all_settings = await svc.get_all_settings()

        bkp = all_settings.backup
        if bkp.backup_enabled and bkp.backup_company_id:
            _add_or_replace_job(bkp.backup_cron)
            logger.info(
                "backup_scheduler_configured",
                cron=bkp.backup_cron,
                company_id=bkp.backup_company_id,
            )
        else:
            logger.info("backup_scheduler_skipped", reason="disabled_or_no_company")

        scheduler.start()
        logger.info("scheduler_started")
    except Exception as exc:
        logger.error("scheduler_init_failed", error=str(exc))


def reschedule_backup(cron_expression: str, enabled: bool = True) -> None:
    """Update the backup job schedule at runtime.

    Called from the settings save handler so that changes take effect
    immediately without an application restart.
    """
    if not enabled:
        if scheduler.get_job(_JOB_ID):
            scheduler.remove_job(_JOB_ID)
            logger.info("backup_job_removed")
        return

    _add_or_replace_job(cron_expression)
    logger.info("backup_job_rescheduled", cron=cron_expression)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _add_or_replace_job(cron_expression: str) -> None:
    """Add the backup job or replace it with a new trigger."""
    trigger = CronTrigger.from_crontab(cron_expression)
    existing = scheduler.get_job(_JOB_ID)
    if existing:
        scheduler.reschedule_job(_JOB_ID, trigger=trigger)
    else:
        scheduler.add_job(
            _scheduled_backup_job,
            trigger=trigger,
            id=_JOB_ID,
            name="Database Backup",
            replace_existing=True,
        )
