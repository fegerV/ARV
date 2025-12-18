from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class VideoCreate(BaseModel):
    ar_content_id: UUID
    filename: str = Field(..., min_length=1, description="Video filename from file upload")
    set_as_active: Optional[bool] = Field(default=False, description="Set this video as the active one")
    
    class Config:
        from_attributes = True


class VideoUpdate(BaseModel):
    video_status: Optional[str] = None
    
    class Config:
        from_attributes = True


class VideoResponse(BaseModel):
    id: UUID
    ar_content_id: UUID
    filename: str
    duration: Optional[int] = None
    size: Optional[int] = None
    video_status: str
    created_at: str
    
    class Config:
        from_attributes = True