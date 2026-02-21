"""
AR Content API schemas for the flat API structure.
"""
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, EmailStr


class ARContentListItem(BaseModel):
    """Schema for AR content item in list view."""
    id: str
    order_number: str
    company_name: str
    company_id: str
    project_id: str
    project_name: str
    created_at: str
    status: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    photo_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    active_video_url: Optional[str] = None
    active_video_title: Optional[str] = None
    views_count: int
    views_30_days: Optional[int] = None
    public_link: str
    public_url: Optional[str] = None
    has_qr_code: Optional[bool] = None
    qr_code_url: Optional[str] = None
    _links: Dict[str, str]


class ARContentListResponse(BaseModel):
    """Schema for AR content list response with pagination."""
    items: List[ARContentListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class ARContentCreateRequest(BaseModel):
    """Schema for creating new AR content."""
    company_id: int = Field(..., description="Company ID")
    project_id: str = Field(..., description="Project ID")
    customer_name: Optional[str] = Field(None, description="Customer name")
    customer_phone: Optional[str] = Field(None, description="Customer phone")
    customer_email: Optional[EmailStr] = Field(None, description="Customer email")
    duration_years: int = Field(30, description="Duration in years (default: 30)")


class ARContentUpdateRequest(BaseModel):
    """Schema for updating AR content."""
    customer_name: Optional[str] = Field(None, description="Customer name")
    customer_phone: Optional[str] = Field(None, description="Customer phone")
    customer_email: Optional[EmailStr] = Field(None, description="Customer email")
    status: Optional[str] = Field(None, description="Status")
    duration_years: Optional[int] = Field(None, description="Duration in years")


class VideoItem(BaseModel):
    """Schema for video item in AR content details."""
    id: str
    filename: str
    uploaded_at: str
    is_active: bool
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = None
    size: Optional[int] = None
    status: str
    _links: Dict[str, str]


class ARContentStats(BaseModel):
    """Schema for AR content statistics."""
    views: int
    last_viewed: Optional[str] = None


class ARContentDetailResponse(BaseModel):
    """Schema for detailed AR content response."""
    id: str
    order_number: str
    company_name: str
    company_id: str
    project_id: str
    project_name: str
    created_at: str
    status: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    duration_years: int
    photo_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    active_video_url: Optional[str] = None
    active_video_title: Optional[str] = None
    views_count: int
    views_30_days: Optional[int] = None
    public_link: str
    public_url: Optional[str] = None
    has_qr_code: Optional[bool] = None
    qr_code_url: Optional[str] = None
    marker_url: Optional[str] = None
    marker_preview_url: Optional[str] = None
    videos: List[VideoItem] = []
    stats: ARContentStats
    _links: Dict[str, str]


class ARContentCreateResponse(BaseModel):
    """Schema for AR content creation response."""
    id: str
    order_number: str
    public_link: str
    qr_code_url: str
    marker_url: Optional[str] = None
    photo_url: Optional[str] = None
    video_url: Optional[str] = None


class VideoResponse(BaseModel):
    """Schema for video response."""
    id: str
    ar_content_id: str
    filename: str
    duration: Optional[int] = None
    size: Optional[int] = None
    status: str
    uploaded_at: str
    is_active: bool
    thumbnail_url: Optional[str] = None
    _links: Dict[str, str]


class VideoListResponse(BaseModel):
    """Schema for video list response."""
    items: List[VideoResponse]
    total: int