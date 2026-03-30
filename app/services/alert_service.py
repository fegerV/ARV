from dataclasses import dataclass
from typing import List
from datetime import datetime, UTC

import httpx
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import structlog

from app.core.config import settings

logger = structlog.get_logger()


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)

@dataclass
class Alert:
    severity: str  # "critical", "warning", "info"
    title: str
    message: str
    metrics: dict
    affected_services: List[str]

async def publish_alerts(alerts: List[Alert]) -> None:
    # Redis removed: no-op (keep API stable)
    return None


ALERT_COOLDOWN_SECONDS = {
    "critical": 300,  # 5 минут
    "warning": 900,   # 15 минут
    "info": 3600      # 1 час
}


async def send_critical_alerts(alerts: List[Alert], metrics: dict) -> None:
    """Отправка критических алертов (без Redis cooldown)."""
    pending_alerts: List[Alert] = alerts

    if not pending_alerts:
        return

    # Email
    await send_admin_email(pending_alerts, metrics)
    # Telegram
    await send_telegram_alerts(pending_alerts, metrics)
    await publish_alerts(pending_alerts)


async def send_admin_email(alerts: List[Alert], metrics: dict) -> None:
    """Email уведомление администратору."""
    msg = MIMEMultipart()
    msg['Subject'] = f"🚨 Vertex AR Alert: {len(alerts)} critical issues"
    msg['From'] = settings.SMTP_FROM_EMAIL
    msg['To'] = settings.ADMIN_EMAIL

    html_body = f"""
    <h2>🚨 Vertex AR System Alerts</h2>
    <p><strong>Time:</strong> {_utcnow_naive()}</p>

    <h3>Critical Alerts ({len(alerts)}):</h3>
    {''.join([f'<div style="border:1px solid red;padding:10px;margin:5px;"><h4>{a.title}</h4><p>{a.message}</p></div>' for a in alerts])}

    <h3>System Metrics:</h3>
    <ul>
      <li>CPU: {metrics.get('cpu_percent', 'n/a')}%</li>
      <li>Memory: {metrics.get('memory_percent', 'n/a')}%</li>
      <li>API Health: {metrics.get('api_health', 'n/a')}</li>
    </ul>

    <p><a href="{settings.ADMIN_FRONTEND_URL}">View Dashboard</a></p>
    """
    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("critical_alert_email_sent", count=len(alerts))
    except Exception as e:
        logger.error("critical_alert_email_failed", error=str(e))


async def send_telegram_alerts(alerts: List[Alert], metrics: dict) -> None:
    """Telegram уведомления (админ-чат). Использует настройки из БД, иначе из env."""
    bot_token: str | None = None
    admin_chat_id: str | None = None

    try:
        from app.core.database import AsyncSessionLocal
        from app.services.settings_service import SettingsService
        async with AsyncSessionLocal() as session:
            svc = SettingsService(session)
            all_settings = await svc.get_all_settings()
            n = all_settings.notifications
            if n.telegram_enabled and n.telegram_bot_token and n.telegram_admin_chat_id:
                bot_token = n.telegram_bot_token
                admin_chat_id = n.telegram_admin_chat_id
    except Exception as e:
        logger.warning("alert_telegram_settings_load_failed", error=str(e))

    if not bot_token or not admin_chat_id:
        bot_token = settings.TELEGRAM_BOT_TOKEN
        admin_chat_id = settings.TELEGRAM_ADMIN_CHAT_ID

    if not bot_token or not admin_chat_id:
        logger.warning("telegram_not_configured")
        return

    message = f"""
🚨 <b>Vertex AR Alerts</b>

<strong>Critical ({len(alerts)}):</strong>
{chr(10).join([f"• {a.title}: {a.message}" for a in alerts])}

<strong>Metrics:</strong>
CPU: {metrics.get('cpu_percent', 'n/a')}%
RAM: {metrics.get('memory_percent', 'n/a')}%
API: {metrics.get('api_health', 'n/a')}

<a href="{settings.ADMIN_FRONTEND_URL}">📊 Dashboard</a>
"""

    await send_telegram_message(chat_id=admin_chat_id, message=message, bot_token=bot_token)


async def send_telegram_message(chat_id: str, message: str, bot_token: str | None = None) -> None:
    token = bot_token or settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.warning("telegram_bot_token_missing")
        return
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=10.0,
            )
            if resp.status_code == 200:
                logger.info("telegram_alert_sent", chat_id=chat_id)
            else:
                logger.error("telegram_alert_failed", status=resp.status_code)
    except Exception as e:
        logger.error("telegram_alert_error", error=str(e))


# Simple class to act as a service
class AlertService:
    def __init__(self):
        pass

    async def publish_alerts(self, alerts: List[Alert]) -> None:
        return await publish_alerts(alerts)

    async def send_critical_alerts(self, alerts: List[Alert], metrics: dict) -> None:
        return await send_critical_alerts(alerts, metrics)

    async def send_admin_email(self, alerts: List[Alert], metrics: dict) -> None:
        return await send_admin_email(alerts, metrics)

    async def send_telegram_alerts(self, alerts: List[Alert], metrics: dict) -> None:
        return await send_telegram_alerts(alerts, metrics)

    async def send_telegram_message(self, chat_id: str, message: str) -> None:
        return await send_telegram_message(chat_id, message)


# Singleton instance
alert_service = AlertService()
