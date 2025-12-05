from dataclasses import dataclass
from typing import List
from datetime import datetime
import asyncio
import json

import httpx
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import redis.asyncio as redis
import structlog

from app.core.config import settings
async def publish_alerts(alerts: List[Alert]) -> None:
    try:
        r = redis.from_url(settings.REDIS_URL)
        for a in alerts:
            msg = {"severity": a.severity, "title": a.title, "message": a.message, "services": a.affected_services}
            payload = json.dumps(msg)
            await r.publish("alerts", payload)
            # store a short history for /alerts and /logs commands
            await r.lpush("alerts_history", payload)
            await r.ltrim("alerts_history", 0, 99)
        await r.aclose()
    except Exception as e:
        logger.error("publish_alerts_error", error=str(e))


@dataclass
class Alert:
    severity: str  # "critical", "warning", "info"
    title: str
    message: str
    metrics: dict
    affected_services: List[str]


ALERT_COOLDOWN_SECONDS = {
    "critical": 300,  # 5 минут
    "warning": 900,   # 15 минут
    "info": 3600      # 1 час
}


async def send_critical_alerts(alerts: List[Alert], metrics: dict) -> None:
    """Отправка критических алертов с cooldown через Redis."""
    # Filter by cooldown
    pending_alerts: List[Alert] = []
    try:
        r = redis.from_url(settings.REDIS_URL)
        for alert in alerts:
            key = f"alert:{alert.severity}:{alert.title}"
            exists = await r.exists(key)
            if not exists:
                pending_alerts.append(alert)
                await r.set(key, "1", ex=ALERT_COOLDOWN_SECONDS.get(alert.severity, 300))
        await r.aclose()
    except Exception as e:
        logger.error("alert_cooldown_error", error=str(e))
        pending_alerts = alerts  # fallback: send anyway

    if not pending_alerts:
        return

    # Email
    await send_admin_email(pending_alerts, metrics)
    # Telegram
    await send_telegram_alerts(pending_alerts, metrics)
    # WebSocket broadcast via Redis pubsub
    await publish_alerts(pending_alerts)


async def send_admin_email(alerts: List[Alert], metrics: dict) -> None:
    """Email уведомление администратору."""
    msg = MIMEMultipart()
    msg['Subject'] = f"🚨 Vertex AR Alert: {len(alerts)} critical issues"
    msg['From'] = settings.SMTP_FROM_EMAIL
    msg['To'] = settings.ADMIN_EMAIL

    html_body = f"""
    <h2>🚨 Vertex AR System Alerts</h2>
    <p><strong>Time:</strong> {datetime.utcnow()}</p>

    <h3>Critical Alerts ({len(alerts)}):</h3>
    {''.join([f'<div style="border:1px solid red;padding:10px;margin:5px;"><h4>{a.title}</h4><p>{a.message}</p></div>' for a in alerts])}

    <h3>System Metrics:</h3>
    <ul>
      <li>CPU: {metrics.get('cpu_percent', 'n/a')}%</li>
      <li>Memory: {metrics.get('memory_percent', 'n/a')}%</li>
      <li>Queue: {metrics.get('celery_queue_length', 'n/a')}</li>
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
    """Telegram уведомления (админ-чат)."""
    admin_chat_id = settings.TELEGRAM_ADMIN_CHAT_ID
    if not settings.TELEGRAM_BOT_TOKEN or not admin_chat_id:
        logger.warning("telegram_not_configured")
        return

    message = f"""
🚨 <b>Vertex AR Alerts</b>

<strong>Critical ({len(alerts)}):</strong>
{chr(10).join([f"• {a.title}: {a.message}" for a in alerts])}

<strong>Metrics:</strong>
CPU: {metrics.get('cpu_percent', 'n/a')}%
RAM: {metrics.get('memory_percent', 'n/a')}%
Queue: {metrics.get('celery_queue_length', 'n/a')}
API: {metrics.get('api_health', 'n/a')}

<a href="{settings.ADMIN_FRONTEND_URL}">📊 Dashboard</a>
"""

    await send_telegram_message(admin_chat_id, message)


async def send_telegram_message(chat_id: str, message: str) -> None:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
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
