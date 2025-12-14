from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


class VideoScheduleBase(BaseModel):
    start_time: datetime
    end_time: datetime
    description: Optional[str] = Field(None, max_length=500)


class VideoScheduleCreate(VideoScheduleBase):
    video_id: UUID


class VideoScheduleUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    description: Optional[str] = Field(None, max_length=500)


class VideoScheduleInDBBase(VideoScheduleBase):
    id: UUID
    video_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VideoSchedule(VideoScheduleInDBBase):
    pass


class VideoSubscriptionUpdate(BaseModel):
    subscription: str  # Can be '1y', '2y', or ISO date string


class VideoRotationUpdate(BaseModel):
    rotation_type: str = Field(..., pattern="^(none|sequential|cyclic)$")


class VideoSetActiveResponse(BaseModel):
    status: str
    active_video_id: UUID
    message: str


class VideoStatusResponse(BaseModel):
    id: UUID
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