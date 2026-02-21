from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class VideoScheduleBase(BaseModel):
    start_time: datetime
    end_time: datetime
    description: Optional[str] = Field(None, max_length=500)


class VideoScheduleCreate(VideoScheduleBase):
    video_id: int


class VideoScheduleUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    description: Optional[str] = Field(None, max_length=500)


class VideoScheduleInDBBase(VideoScheduleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: int
    status: str
    created_at: datetime
    updated_at: datetime


class VideoSchedule(VideoScheduleInDBBase):
    pass


class VideoSubscriptionUpdate(BaseModel):
    subscription: str  # Can be '1y', '2y', or ISO date string


class VideoRotationUpdate(BaseModel):
    rotation_type: str = Field(..., pattern="^(none|sequential|cyclic)$")


class VideoActiveUpdate(BaseModel):
    is_active: bool


class VideoPlaybackModeUpdate(BaseModel):
    mode: str = Field(..., pattern="^(manual|sequential|cyclic)$")
    active_video_id: Optional[int] = None
    active_video_ids: Optional[List[int]] = None


class VideoSetActiveResponse(BaseModel):
    status: str
    active_video_id: int
    message: str


class VideoStatusResponse(BaseModel):
    id: int
    title: Optional[str]
    video_url: Optional[str]
    preview_url: Optional[str]
    is_active: bool
    rotation_type: str
    subscription_end: Optional[datetime]
    status: str  # Computed: active, expiring, expired
    days_remaining: Optional[int]  # Computed
    schedules_count: int  # Count of attached schedules
    schedules_summary: List[dict]  # Summary of schedule windows