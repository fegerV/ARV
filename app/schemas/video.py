from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class VideoBase(BaseModel):
    ar_content_id: int
    
    # File information
    file_path: str = Field(..., max_length=500)
    public_url: Optional[str] = Field(None, max_length=500)
    video_path: str = Field(..., max_length=500)
    video_url: Optional[str] = Field(None, max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    preview_url: Optional[str] = Field(None, max_length=500)
    
    # Video metadata
    title: Optional[str] = Field(None, max_length=255)
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    size_bytes: Optional[int] = None
    mime_type: Optional[str] = Field(None, max_length=100)
    
    # Status
    status: str = Field(default="active", max_length=50)
    is_active: bool = False
    
    # Subscription management
    subscription_end: Optional[datetime] = None
    
    # Rotation management
    rotation_type: str = Field(default="none", max_length=20)
    rotation_order: int = 0


class VideoCreate(VideoBase):
    pass


class VideoUpdate(BaseModel):
    ar_content_id: Optional[int] = None
    
    # File information
    file_path: Optional[str] = Field(None, max_length=500)
    public_url: Optional[str] = Field(None, max_length=500)
    video_path: Optional[str] = Field(None, max_length=500)
    video_url: Optional[str] = Field(None, max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    preview_url: Optional[str] = Field(None, max_length=500)
    
    # Video metadata
    title: Optional[str] = Field(None, max_length=255)
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    size_bytes: Optional[int] = None
    mime_type: Optional[str] = Field(None, max_length=100)
    
    # Status
    status: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    
    # Subscription management
    subscription_end: Optional[datetime] = None
    
    # Rotation management
    rotation_type: Optional[str] = Field(None, max_length=20)
    rotation_order: Optional[int] = None


class VideoInDBBase(VideoBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Video(VideoInDBBase):
    pass


class VideoResponse(Video):
    pass