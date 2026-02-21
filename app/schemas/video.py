from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class VideoCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ar_content_id: int
    filename: str = Field(..., min_length=1, description="Video filename from file upload")
    set_as_active: Optional[bool] = Field(default=False, description="Set this video as the active one")


class VideoUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    video_status: Optional[str] = None


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ar_content_id: int
    filename: str
    duration: Optional[int] = None
    size: Optional[int] = None
    video_status: str
    created_at: str