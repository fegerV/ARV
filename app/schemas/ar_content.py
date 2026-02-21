from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from app.enums import ArContentStatus


class ArContentCreate(BaseModel):
    project_id: int
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    duration_years: int = Field(default=30)
    
    class Config:
        from_attributes = True


class ArContentUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    status: Optional[ArContentStatus] = None
    duration_years: Optional[int] = None
    
    class Config:
        from_attributes = True


class VideoResponse(BaseModel):
    id: int
    ar_content_id: int
    filename: str
    duration: Optional[int] = None
    size: Optional[int] = None
    status: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class ArContentResponse(BaseModel):
    id: int
    order_number: str
    project_id: int
    company_id: int
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    duration_years: int
    views_count: int
    status: str
    active_video_id: Optional[int] = None
    public_link: Optional[str] = None  # Optional for legacy/incomplete records
    qr_code_url: Optional[str] = None
    photo_url: Optional[str] = None
    thumbnail_url: Optional[str] = None  # Thumbnail URL for photo preview
    video_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ArContentDetailResponse(ArContentResponse):
    videos: List[VideoResponse] = []
    active_video: Optional[VideoResponse] = None
    
    class Config:
        from_attributes = True


# Additional schemas for API compatibility
class ARContent(ArContentResponse):
    """Alias for ArContentResponse for backward compatibility"""
    pass


class ARContentVideoUpdate(BaseModel):
    """Schema for updating the active video of AR content"""
    active_video_id: int
    
    class Config:
        from_attributes = True


class ARContentList(BaseModel):
    """Schema for AR content list response"""
    items: List[ArContentResponse]
    total: int = Field(..., description="Total number of AR content items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    
    class Config:
        from_attributes = True


class ARContentCreateResponse(BaseModel):
    """Schema for AR content creation response"""
    id: int
    order_number: str
    public_link: str
    qr_code_url: str
    photo_url: str
    video_url: str
    photo_analysis: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class ARContentWithLinks(BaseModel):
    """Schema for AR content with additional links"""
    id: int
    order_number: str
    unique_id: Optional[str] = None  # UUID for /view/{unique_id}
    unique_link: Optional[str] = None
    public_url: Optional[str] = None  # Public URL for AR viewer
    company_id: int  # Company ID
    project_id: int  # Project ID
    storage_path: Optional[str] = None  # Local storage path

    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    duration_years: Optional[int] = None

    qr_code_url: str
    photo_url: str
    thumbnail_url: Optional[str] = None  # Thumbnail URL for photo preview
    video_url: str
    views_count: int
    status: str
    created_at: datetime
    updated_at: datetime

    company_name: Optional[str] = None  # Company name
    project_name: Optional[str] = None  # Project name
    marker_url: Optional[str] = None  # URL to the AR marker file
    marker_status: Optional[str] = None  # Status of marker generation
    marker_metadata: Optional[Dict[str, Any]] = None  # Additional marker metadata
    videos: List[VideoResponse] = []
    active_video: Optional[VideoResponse] = None

    class Config:
        from_attributes = True


# Aliases for backward compatibility with existing API routes
ARContentCreate = ArContentCreate
ARContentUpdate = ArContentUpdate