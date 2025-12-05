import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()


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
Команда Vertex AR
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
