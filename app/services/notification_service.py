import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx
import structlog
from typing import Optional, Dict, Any
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.notification import Notification

logger = structlog.get_logger()


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def create_notification(
    db: AsyncSession,
    notification_type: str,
    subject: str,
    message: str,
    company_id: Optional[int] = None,
    project_id: Optional[int] = None,
    ar_content_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Notification:
    """Create a notification in the database.
    
    Args:
        db: Database session
        notification_type: Type of notification (e.g., 'ar_content_created', 'project_expired')
        subject: Notification subject/title
        message: Notification message
        company_id: Optional company ID
        project_id: Optional project ID
        ar_content_id: Optional AR content ID
        metadata: Optional metadata dictionary
        
    Returns:
        Created Notification object
    """
    try:
        notification = Notification(
            notification_type=notification_type,
            subject=subject,
            message=message,
            company_id=company_id,
            project_id=project_id,
            ar_content_id=ar_content_id,
            notification_metadata=metadata or {},
            created_at=_utcnow_naive()
        )
        
        db.add(notification)
        await db.flush()
        await db.commit()
        await db.refresh(notification)
        
        logger.info("notification_created",
                   notification_id=notification.id,
                   notification_type=notification_type)
        
        return notification
    except Exception as e:
        logger.error("error_creating_notification",
                    error=str(e),
                    notification_type=notification_type)
        await db.rollback()
        raise


def send_expiry_warning_email(project_name: str, company_email: str, expires_at_str: str, ar_items_count: int) -> bool:
    subject = f"⚠️ Проект '{project_name}' истекает через 7 дней"
    body = f"""
Здравствуйте!

Ваш AR-проект скоро истечет:

📁 Проект: {project_name}
📅 Дата истечения: {expires_at_str}
🎬 AR-контент: {ar_items_count} элементов

Для продления подписки свяжитесь с нами:
📧 Email: support@vertexar.com
📱 Телефон: +7 (999) 123-45-67

--
С уважением,
Команда V-Portal
"""
    msg = MIMEMultipart()
    msg['From'] = settings.SMTP_FROM_EMAIL
    msg['To'] = company_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("expiry_warning_email_sent", project=project_name)
        return True
    except Exception as e:
        logger.error("expiry_warning_email_failed", error=str(e))
        return False


async def send_expiry_warning_telegram(company_chat_id: str, project_name: str, expires_at_str: str, ar_items_count: int) -> bool:
    message = f"""
⚠️ <b>Проект скоро истечет!</b>

📁 Проект: <b>{project_name}</b>
📅 Истекает: <b>{expires_at_str}</b>
🎬 AR-контент: {ar_items_count} элементов

Для продления свяжитесь с нами:
📧 support@vertexar.com
📱 +7 (999) 123-45-67
"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": company_chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                },
            )
            ok = resp.status_code == 200
            if ok:
                logger.info("expiry_warning_telegram_sent", project=project_name)
            else:
                logger.error("telegram_send_failed", status=resp.status_code)
            return ok
    except Exception as e:
        logger.error("telegram_send_error", error=str(e))
        return False


# Create a simple class to act as a service
class NotificationService:
    def __init__(self):
        pass

    async def create_notification(
        self,
        db: AsyncSession,
        notification_type: str,
        subject: str,
        message: str,
        company_id: Optional[int] = None,
        project_id: Optional[int] = None,
        ar_content_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        return await create_notification(
            db, notification_type, subject, message,
            company_id, project_id, ar_content_id, metadata
        )

    def send_expiry_warning_email(self, project_name: str, company_email: str, expires_at_str: str, ar_items_count: int) -> bool:
        return send_expiry_warning_email(project_name, company_email, expires_at_str, ar_items_count)

    async def send_expiry_warning_telegram(self, company_chat_id: str, project_name: str, expires_at_str: str, ar_items_count: int) -> bool:
        return await send_expiry_warning_telegram(company_chat_id, project_name, expires_at_str, ar_items_count)


# Singleton instance
notification_service = NotificationService()
