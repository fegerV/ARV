from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class VideoSchedule(Base):
    __tablename__ = "video_schedules"
    __table_args__ = (
        CheckConstraint('start_time <= end_time', name='check_schedule_time_range'),
    )

    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    
    # Schedule time window
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    
    # Status automatically computed based on current time
    status = Column(String(20), default="active")  # 'active', 'expired'
    
    # Optional description for the schedule
    description = Column(String(500))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    video = relationship("Video", back_populates="schedules")