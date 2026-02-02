from sqlalchemy import Column, Integer, String, Time, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid
from datetime import datetime


class VideoRotationSchedule(Base):
    """Video rotation schedule with support for multiple rotation types and date-specific rules"""
    __tablename__ = "video_rotation_schedules"
    
    # Use Integer as primary key to match migration
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to AR content
    ar_content_id = Column(Integer, ForeignKey("ar_content.id", ondelete="CASCADE"), nullable=False)

    # Rotation type: fixed, date_specific, daily_cycle, weekly_cycle, monthly_cycle, random_daily, priority_rules
    rotation_type = Column(String(50), nullable=False, default="fixed")
    
    # Default video (for fixed and as fallback)
    default_video_id = Column(Integer, ForeignKey("videos.id"), nullable=True)

    # Date-specific rules (JSONB for PostgreSQL, JSON for SQLite)
    # Format: [{"date": "2025-12-31", "video_id": 2, "recurring": true}, ...]
    # recurring=true means this date applies every year
    date_rules = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True, default=list)

    # For cycles: ordered list of video IDs
    video_sequence = Column(JSON, nullable=True, default=list)
    current_index = Column(Integer, default=0)

    # For random_daily: seed for reproducibility
    random_seed = Column(String(32), nullable=True)
    no_repeat_days = Column(Integer, default=1)  # Don't repeat same video for N days

    # Cron-like schedule (optional)
    cron_expression = Column(String(100), nullable=True)
    time_of_day = Column(Time, nullable=True)
    day_of_week = Column(Integer, nullable=True)  # 0-6 (Monday=0)
    day_of_month = Column(Integer, nullable=True)  # 1-31

    # Status and timing
    is_active = Column(Boolean, default=True, nullable=False)
    next_change_at = Column(DateTime, nullable=True)  # When next rotation should happen
    last_changed_at = Column(DateTime, nullable=True)
    
    # Notification settings
    notify_before_expiry_days = Column(Integer, default=7, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    ar_content = relationship("ARContent", backref="rotation_schedules")
    default_video_rel = relationship("Video", foreign_keys=[default_video_id], post_update=True)