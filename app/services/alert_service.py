from dataclasses import dataclass
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

import httpx
import smtplib
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


async def _load_notification_settings():
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.settings_service import SettingsService

        async with AsyncSessionLocal() as session:
            svc = SettingsService(session)
            return (await svc.get_all_settings()).notifications
    except Exception as exc:
        logger.warning("alert_telegram_settings_load_failed", error=str(exc))
        return None


def _alert_matches_kind(alert: Alert, kind: str) -> bool:
    haystack = " ".join(
        [
            alert.severity,
            alert.title,
            alert.message,
            " ".join(alert.affected_services or []),
        ]
    ).lower()
    return kind in haystack


def _telegram_alerts_enabled(notification_settings, alerts: List[Alert]) -> bool:
    if not notification_settings or not getattr(notification_settings, "telegram_alerts_enabled", False):
        return False

    checks = [
        (getattr(notification_settings, "alert_on_critical", True), lambda alert: alert.severity == "critical"),
        (getattr(notification_settings, "alert_on_warning", False), lambda alert: alert.severity == "warning"),
        (getattr(notification_settings, "alert_on_backup_failed", True), lambda alert: _alert_matches_kind(alert, "backup")),
        (getattr(notification_settings, "alert_on_storage_failed", True), lambda alert: _alert_matches_kind(alert, "storage")),
        (getattr(notification_settings, "alert_on_health_degraded", True), lambda alert: _alert_matches_kind(alert, "health") or _alert_matches_kind(alert, "api")),
    ]
    return any(enabled and any(predicate(alert) for alert in alerts) for enabled, predicate in checks)


async def publish_alerts(alerts: List[Alert]) -> None:
    # Redis removed: no-op (keep API stable)
    return None


ALERT_COOLDOWN_SECONDS = {
    "critical": 300,  # 5 minutes
    "warning": 900,   # 15 minutes
    "info": 3600,     # 1 hour
}


async def send_critical_alerts(alerts: List[Alert], metrics: dict) -> None:
    """Send critical alerts without Redis cooldown."""
    pending_alerts: List[Alert] = alerts

    if not pending_alerts:
        return

    await send_admin_email(pending_alerts, metrics)
    await send_telegram_alerts(pending_alerts, metrics)
    await publish_alerts(pending_alerts)


async def send_admin_email(alerts: List[Alert], metrics: dict) -> None:
    """Send an admin email for critical alerts."""
    notification_settings = await _load_notification_settings()
    smtp_host = settings.SMTP_HOST
    smtp_port = settings.SMTP_PORT
    smtp_username = settings.SMTP_USERNAME
    smtp_password = settings.SMTP_PASSWORD
    smtp_from_email = settings.SMTP_FROM_EMAIL

    if notification_settings and getattr(notification_settings, "email_enabled", False) and getattr(notification_settings, "smtp_host", None):
        smtp_host = notification_settings.smtp_host
        smtp_port = notification_settings.smtp_port
        smtp_username = getattr(notification_settings, "smtp_username", "") or ""
        smtp_password = getattr(notification_settings, "smtp_password", "") or ""
        smtp_from_email = notification_settings.smtp_from_email

    msg = MIMEMultipart()
    msg["Subject"] = f"V-Portal Alert: {len(alerts)} critical issues"
    msg["From"] = smtp_from_email
    msg["To"] = settings.ADMIN_EMAIL

    html_body = f"""
    <h2>V-Portal System Alerts</h2>
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
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)
            server.send_message(msg)
        logger.info("critical_alert_email_sent", count=len(alerts))
    except Exception as exc:
        logger.error("critical_alert_email_failed", error=str(exc))


async def send_telegram_alerts(alerts: List[Alert], metrics: dict) -> None:
    """Send admin Telegram alerts using DB settings first, then env fallback."""
    notification_settings = await _load_notification_settings()
    bot_token: str | None = None
    admin_chat_id: str | None = None

    if (
        notification_settings
        and getattr(notification_settings, "telegram_enabled", False)
        and getattr(notification_settings, "telegram_bot_token", None)
        and getattr(notification_settings, "telegram_admin_chat_id", None)
    ):
        bot_token = notification_settings.telegram_bot_token
        admin_chat_id = notification_settings.telegram_admin_chat_id

    if not bot_token or not admin_chat_id:
        bot_token = settings.TELEGRAM_BOT_TOKEN
        admin_chat_id = settings.TELEGRAM_ADMIN_CHAT_ID

    if not bot_token or not admin_chat_id:
        logger.warning("telegram_not_configured")
        return

    if notification_settings and not _telegram_alerts_enabled(notification_settings, alerts):
        logger.info("telegram_alert_skipped_by_settings", count=len(alerts))
        return

    message = f"""
<b>V-Portal Alerts</b>

<strong>Critical ({len(alerts)}):</strong>
{chr(10).join([f"- {a.title}: {a.message}" for a in alerts])}

<strong>Metrics:</strong>
CPU: {metrics.get('cpu_percent', 'n/a')}%
RAM: {metrics.get('memory_percent', 'n/a')}%
API: {metrics.get('api_health', 'n/a')}

<a href="{settings.ADMIN_FRONTEND_URL}">Dashboard</a>
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
    except Exception as exc:
        logger.error("telegram_alert_error", error=str(exc))


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


alert_service = AlertService()
