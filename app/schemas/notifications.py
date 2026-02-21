"""
Notifications schemas for request/response models.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class NotificationItem(BaseModel):
    """Single notification item."""
    id: int
    title: Optional[str] = None
    message: Optional[str] = None
    type: str
    is_read: bool = False
    read_at: Optional[datetime] = None
    created_at: datetime
    metadata: Optional[dict] = None
    company_name: Optional[str] = None
    project_name: Optional[str] = None
    ar_content_name: Optional[str] = None


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
