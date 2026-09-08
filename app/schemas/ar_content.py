from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, EmailStr
from app.enums import ArContentStatus


class ArContentCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: int
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_email: EmailStr | None = None
    duration_years: int = Field(default=30)


class ArContentUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: int | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_email: EmailStr | None = None
    status: ArContentStatus | None = None
    duration_years: int | None = None


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ar_content_id: int
    filename: str
    duration: int | None = None
    size: int | None = None
    status: str
    is_active: bool
    created_at: datetime


class ArContentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    project_id: int
    company_id: int
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_email: str | None = None
    duration_years: int
    views_count: int
    status: str
    active_video_id: int | None = None
    public_link: str | None = None  # Optional for legacy/incomplete records
    qr_code_url: str | None = None
    photo_url: str | None = None
    thumbnail_url: str | None = None  # Thumbnail URL for photo preview
    video_url: str | None = None
    created_at: datetime
    updated_at: datetime


class ArContentDetailResponse(ArContentResponse):
    model_config = ConfigDict(from_attributes=True)

    videos: list[VideoResponse] = []
    active_video: VideoResponse | None = None


# Additional schemas for API compatibility
class ARContent(ArContentResponse):
    """Alias for ArContentResponse for backward compatibility."""

    pass


class ARContentVideoUpdate(BaseModel):
    """Schema for updating the active video of AR content."""

    model_config = ConfigDict(from_attributes=True)

    active_video_id: int


class ARContentList(BaseModel):
    """Schema for AR content list response."""

    model_config = ConfigDict(from_attributes=True)

    items: list[ArContentResponse]
    total: int = Field(..., description="Total number of AR content items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")


class ARContentCreateResponse(BaseModel):
    """Schema for AR content creation response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    public_link: str
    qr_code_url: str
    photo_url: str
    video_url: str
    photo_analysis: dict[str, Any] | None = None


class ARContentWithLinks(BaseModel):
    """Schema for AR content with additional links"""
    id: int
    order_number: str
    unique_id: str | None = None  # UUID for /view/{unique_id}
    unique_link: str | None = None
    public_url: str | None = None  # Public URL for AR viewer
    company_id: int  # Company ID
    project_id: int  # Project ID
    storage_path: str | None = None  # Local storage path

    customer_name: str | None = None
    customer_phone: str | None = None
    customer_email: str | None = None
    duration_years: int | None = None

    qr_code_url: str
    photo_url: str
    thumbnail_url: str | None = None  # Thumbnail URL for photo preview
    video_url: str
    views_count: int
    status: str
    created_at: datetime
    updated_at: datetime

    company_name: str | None = None  # Company name
    project_name: str | None = None  # Project name
    marker_url: str | None = None  # URL to the AR marker file
    marker_status: str | None = None  # Status of marker generation
    marker_metadata: dict[str, Any] | None = None  # Additional marker metadata
    videos: list[VideoResponse] = []
    active_video: VideoResponse | None = None

    model_config = ConfigDict(from_attributes=True)


# Aliases for backward compatibility with existing API routes
ARContentCreate = ArContentCreate
ARContentUpdate = ArContentUpdate
