from app.tasks.celery_app import celery_app
import structlog
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.project import Project
from app.models.ar_content import ARContent
from app.models.notification import Notification
from app.services.notification_service import send_expiry_warning_email, send_expiry_warning_telegram

logger = structlog.get_logger()

@celery_app.task(name="app.tasks.notification_tasks.check_expiring_content", bind=True)
def check_expiring_content(self):
    """
    Check for AR content and projects expiring in 7 days and notify.
    """
    logger.info("expiry_check_started", task_id=self.request.id)

    async def _run():
        async with AsyncSessionLocal() as db:
            now = datetime.utcnow()
            target_start = (now + timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
            target_end = target_start.replace(hour=23, minute=59, second=59, microsecond=0)

            # AR Content expiring
            res_ac = await db.execute(
                select(ARContent).where(
                    ARContent.expires_at != None,  # noqa: E711
                    ARContent.expires_at.between(target_start, target_end),
                    ARContent.is_active == True,
                )
            )
            for ac in res_ac.scalars().all():
                n = Notification(
                    company_id=ac.company_id,
                    project_id=ac.project_id,
                    ar_content_id=ac.id,
                    notification_type="expiry_warning",
                    subject=f"AR-контент '{ac.title}' истекает через 7 дней",
                    message=f"Срок истекает {ac.expires_at}",
                    metadata={"expires_at": ac.expires_at.isoformat() if ac.expires_at else None},
                )
                db.add(n)
                # Send email/telegram best-effort (company contact info may be separate)
                # Here we just log; integrate with company contact fields if present

            # Projects expiring
            res_pr = await db.execute(
                select(Project).where(
                    Project.expires_at != None,  # noqa: E711
                    Project.expires_at.between(target_start, target_end),
                    Project.status == "active",
                )
            )
            for pr in res_pr.scalars().all():
                n2 = Notification(
                    company_id=pr.company_id,
                    project_id=pr.id,
                    ar_content_id=None,
                    notification_type="expiry_warning",
                    subject=f"Проект '{pr.name}' истекает через 7 дней",
                    message=f"Срок истекает {pr.expires_at}",
                    metadata={"expires_at": pr.expires_at.isoformat() if pr.expires_at else None},
                )
                db.add(n2)
            await db.commit()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run())
    finally:
        loop.close()

    logger.info("expiry_check_completed")
    return {"status": "completed"}


@celery_app.task(name="app.tasks.notification_tasks.send_email_notification", bind=True)
def send_email_notification(self, email: str, subject: str, body: str):
    """
    Send email notification.
    
    Args:
        email: Recipient email address
        subject: Email subject
        body: Email body (HTML)
    """
    logger.info("email_notification_sending", email=email, task_id=self.request.id)
    
    # TODO: Implement email sending
    # This will be implemented in Phase 6
    
    logger.info("email_notification_sent", email=email)
    
    return {"status": "sent", "email": email}


@celery_app.task(name="app.tasks.notification_tasks.send_telegram_notification", bind=True)
def send_telegram_notification(self, chat_id: str, message: str):
    """
    Send Telegram notification.
    
    Args:
        chat_id: Telegram chat ID
        message: Message text
    """
    logger.info("telegram_notification_sending", chat_id=chat_id, task_id=self.request.id)
    
    # TODO: Implement Telegram bot messaging
    # This will be implemented in Phase 6
    
    logger.info("telegram_notification_sent", chat_id=chat_id)
    
    return {"status": "sent", "chat_id": chat_id}
