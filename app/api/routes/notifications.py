from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings
from app.core.database import get_db
from app.models.notification import Notification

router = APIRouter()


def _send_email_notification_sync(to_email: str, subject: str, html_body: str) -> None:
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM_EMAIL
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)


async def _send_telegram_notification_async(chat_id: str, message: str) -> None:
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            timeout=10.0,
        )


@router.get("/notifications")
async def list_notifications(limit: int = 50, db: AsyncSession = Depends(get_db)):
    stmt = select(Notification).order_by(Notification.created_at.desc())
    res = await db.execute(stmt)
    items = res.scalars().all()[:limit]
    return [
        {
            "id": n.id,
            "company_id": n.company_id,
            "project_id": n.project_id,
            "ar_content_id": n.ar_content_id,
            "type": n.notification_type,
            "email_sent": n.email_sent,
            "telegram_sent": n.telegram_sent,
            "subject": n.subject,
            "message": n.message,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in items
    ]


@router.post("/notifications/mark-read")
async def mark_notifications_read(ids: list[int], db: AsyncSession = Depends(get_db)):
    if not ids:
        return {"updated": 0}

    stmt = select(Notification).where(Notification.id.in_(ids))
    res = await db.execute(stmt)
    items = res.scalars().all()

    updated = 0
    for n in items:
        meta = dict(n.notification_metadata or {})
        if not meta.get("is_read"):
            meta["is_read"] = True
            meta["read_at"] = datetime.utcnow().isoformat()
            n.notification_metadata = meta
            updated += 1

    await db.commit()
    return {"updated": updated}


@router.post("/notifications/test")
async def test_notification(email: str, chat_id: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(
        _send_email_notification_sync,
        email,
        "Test Email",
        "<p>Vertex AR test email</p>",
    )
    if settings.TELEGRAM_BOT_TOKEN:
        background_tasks.add_task(
            _send_telegram_notification_async,
            chat_id,
            "Vertex AR test message",
        )
    return {"status": "queued"}
