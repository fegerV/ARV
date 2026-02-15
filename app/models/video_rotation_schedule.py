"""Video rotation schedule model."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, JSON, String, Time
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class VideoRotationSchedule(Base):
    """Video rotation schedule with support for multiple rotation types."""

    __tablename__ = "video_rotation_schedules"

    __table_args__ = (
        Index("ix_vrs_ar_content_id", "ar_content_id"),
    )

    id = Column(Integer, primary_key=True, index=True)

    ar_content_id = Column(Integer, ForeignKey("ar_content.id", ondelete="CASCADE"), nullable=False)

    rotation_type = Column(String(50), nullable=False, default="fixed")
    default_video_id = Column(Integer, ForeignKey("videos.id"), nullable=True)

    # Date-specific rules
    date_rules = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True, default=list)
    video_sequence = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True, default=list)
    current_index = Column(Integer, default=0, nullable=False)

    # Random settings
    random_seed = Column(String(32), nullable=True)
    no_repeat_days = Column(Integer, default=1, nullable=False)

    # Cron-like schedule
    cron_expression = Column(String(100), nullable=True)
    time_of_day = Column(Time, nullable=True)
    day_of_week = Column(Integer, nullable=True)
    day_of_month = Column(Integer, nullable=True)

    # Status and timing
    is_active = Column(Boolean, default=True, nullable=False)
    next_change_at = Column(DateTime, nullable=True)
    last_changed_at = Column(DateTime, nullable=True)

    notify_before_expiry_days = Column(Integer, default=7, nullable=False)

    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    ar_content = relationship("ARContent", backref="rotation_schedules")
    default_video_rel = relationship("Video", foreign_keys=[default_video_id], post_update=True)
