from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class VideoBase(BaseModel):
    ar_content_id: int
    
    video_path: str = Field(..., max_length=500)
    video_url: Optional[str] = Field(None, max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    
    title: Optional[str] = Field(None, max_length=255)
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    size_bytes: Optional[int] = None
    mime_type: Optional[str] = Field(None, max_length=100)
    
    is_active: bool = False
    
    schedule_start: Optional[datetime] = None
    schedule_end: Optional[datetime] = None
    
    rotation_order: int = 0


class VideoCreate(VideoBase):
    pass


class VideoUpdate(BaseModel):
    ar_content_id: Optional[int] = None
    
    video_path: Optional[str] = Field(None, max_length=500)
    video_url: Optional[str] = Field(None, max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    
    title: Optional[str] = Field(None, max_length=255)
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    size_bytes: Optional[int] = None
    mime_type: Optional[str] = Field(None, max_length=100)
    
    is_active: Optional[bool] = None
    
    schedule_start: Optional[datetime] = None
    schedule_end: Optional[datetime] = None
    
    rotation_order: Optional[int] = None


class VideoInDBBase(VideoBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Video(VideoInDBBase):
    pass