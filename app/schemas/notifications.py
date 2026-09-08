"""
Notifications schemas for request/response models.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class NotificationItem(BaseModel):
    """Single notification item."""
    id: int
    title: str | None = None
    message: str | None = None
    type: str
    is_read: bool = False
    read_at: datetime | None = None
    created_at: datetime
    metadata: dict | None = None
    company_name: str | None = None
    project_name: str | None = None
    ar_content_name: str | None = None


class NotificationListResponse(BaseModel):
    """Paginated notifications list response."""
    items: list[NotificationItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class NotificationMarkReadResponse(BaseModel):
    """Response for marking notification as read."""
    success: bool = True
    message: str = "Notification marked as read"


class NotificationDeleteResponse(BaseModel):
    """Response for deleting a notification."""
    success: bool = True
    message: str = "Notification deleted"
