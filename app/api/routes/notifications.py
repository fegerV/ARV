from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.notification import Notification
from app.tasks.notification_tasks import send_email_notification, send_telegram_notification

router = APIRouter(prefix="/notifications", tags=["Notifications"])


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


@router.post("/notifications/test")
async def test_notification(email: str, chat_id: str):
    send_email_notification.delay(email, "Test Email", "<p>Vertex AR test email</p>")
    send_telegram_notification.delay(chat_id, "Vertex AR test message")
    return {"status": "sent"}
