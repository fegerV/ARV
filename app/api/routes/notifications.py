from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
import httpx
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings
from app.core.database import get_db
from app.models.notification import Notification
from app.api.routes.auth import get_current_active_user
from app.schemas.notifications import (
    NotificationItem,
    NotificationListResponse,
    NotificationMarkReadResponse,
    NotificationDeleteResponse
)
from app.models.user import User
from app.services.notification_service import create_notification
from pydantic import BaseModel
from typing import Optional, Dict, Any

router = APIRouter()


class NotificationCreate(BaseModel):
    """Schema for creating a notification."""
    notification_type: str
    subject: str
    message: str
    company_id: Optional[int] = None
    project_id: Optional[int] = None
    ar_content_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


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


@router.get("")
async def list_notifications(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stmt = (
        select(Notification)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(stmt)
    items = res.scalars().all()
    
    # Get total count for pagination — scalar COUNT instead of loading all rows
    count_stmt = select(func.count()).select_from(Notification)
    count_res = await db.execute(count_stmt)
    total = count_res.scalar() or 0
    
    notification_items = []
    for n in items:
        meta = dict(n.notification_metadata or {})
        
        # Extract names from metadata or generate defaults
        company_name = meta.get("company_name")
        project_name = meta.get("project_name") 
        ar_content_name = meta.get("ar_content_name")
        
        # Use subject as title, or generate from type
        title = n.subject or meta.get("title") or n.notification_type.replace("_", " ").title()
        
        notification_items.append(
            NotificationItem(
                id=n.id,
                title=title,
                message=n.message or "",
                type=n.notification_type,
                is_read=bool(meta.get("is_read", False)),
                read_at=meta.get("read_at"),
                created_at=n.created_at,
                metadata=meta,
                company_name=company_name,
                project_name=project_name,
                ar_content_name=ar_content_name,
            )
        )
    
    return NotificationListResponse(
        items=notification_items,
        total=total,
        page=(offset // limit) + 1,
        page_size=limit,
        total_pages=(total + limit - 1) // limit
    )


@router.post("/mark-all-read", response_model=NotificationMarkReadResponse)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    stmt = select(Notification)
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
    return NotificationMarkReadResponse(
        success=True,
        message=f"Marked {updated} notifications as read"
    )


@router.post("/mark-read", response_model=NotificationMarkReadResponse)
async def mark_notifications_read(
    ids: list[int],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not ids:
        return NotificationMarkReadResponse(success=False, message="No notification IDs provided")

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
    return NotificationMarkReadResponse(
        success=True,
        message=f"Marked {updated} notifications as read"
    )


@router.delete("/{notification_id}", response_model=NotificationDeleteResponse)
async def delete_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    n = await db.get(Notification, notification_id)
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")

    await db.delete(n)
    await db.commit()
    return NotificationDeleteResponse(
        success=True,
        message=f"Notification {notification_id} deleted"
    )


@router.post("", response_model=NotificationItem)
async def create_notification_endpoint(
    notification_data: NotificationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new notification."""
    notification = await create_notification(
        db=db,
        notification_type=notification_data.notification_type,
        subject=notification_data.subject,
        message=notification_data.message,
        company_id=notification_data.company_id,
        project_id=notification_data.project_id,
        ar_content_id=notification_data.ar_content_id,
        metadata=notification_data.metadata,
    )
    
    meta = dict(notification.notification_metadata or {})
    return NotificationItem(
        id=notification.id,
        title=notification.subject or notification.notification_type.replace("_", " ").title(),
        message=notification.message or "",
        type=notification.notification_type,
        is_read=bool(meta.get("is_read", False)),
        read_at=meta.get("read_at"),
        created_at=notification.created_at,
        metadata=meta,
        company_name=meta.get("company_name"),
        project_name=meta.get("project_name"),
        ar_content_name=meta.get("ar_content_name"),
    )


@router.post("/test")
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
