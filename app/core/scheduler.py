"""APScheduler integration for periodic database backups.

The scheduler is started during application startup and reads its
configuration from the ``backup`` section of system settings.  When
backup settings are changed via the admin panel the schedule is
re-applied at runtime without restarting the application.
"""

from __future__ import annotations

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.database import AsyncSessionLocal
from app.services.settings_service import SettingsService

logger = structlog.get_logger()

_JOB_ID = "db_backup"

scheduler = AsyncIOScheduler()


async def _scheduled_backup_job() -> None:
    """Entry-point executed by APScheduler on each trigger."""
    logger.info("scheduled_backup_triggered")

    async with AsyncSessionLocal() as session:
        svc = SettingsService(session)
        all_settings = await svc.get_all_settings()

    bkp = all_settings.backup
    if not bkp.backup_enabled or not bkp.backup_company_id:
        logger.info("scheduled_backup_skipped", reason="disabled_or_no_company")
        return

    from app.services.backup_service import BackupService

    service = BackupService()
    await service.run_backup(
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
