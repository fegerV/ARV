from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid
from datetime import datetime


class VideoSchedule(Base):
    __tablename__ = "video_schedules"
    __table_args__ = (
        CheckConstraint('start_time <= end_time', name='check_schedule_time_range'),
    )

    # Use Integer as primary key to match migration
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    
    # Schedule time window
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    
    # Status automatically computed based on current time
    status = Column(String(20), default="active")  # 'active', 'expired'
    
    # Optional description for the schedule
    description = Column(String(500))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    video = relationship("Video", back_populates="schedules")