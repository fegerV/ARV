"""
Notifications schemas for request/response models.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class NotificationItem(BaseModel):
    """Single notification item."""
    id: int
    title: str
    message: str
    type: str
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    metadata: Optional[dict] = None


class NotificationListResponse(BaseModel):
    """Paginated notifications list response."""
    items: List[NotificationItem]
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
