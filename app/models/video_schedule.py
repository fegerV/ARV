from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class VideoSchedule(BaseModel):
    __tablename__ = "video_schedules"
    __table_args__ = (
        CheckConstraint('start_time <= end_time', name='check_schedule_time_range'),
    )

    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    
    # Schedule time window
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    
    # Status automatically computed based on current time
    status = Column(String(20), default="active")  # 'active', 'expired'
    
    # Optional description for the schedule
    description = Column(String(500))
    
    # Relationships
    video = relationship("Video", back_populates="schedules")