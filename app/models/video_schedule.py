"""Video schedule model."""

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class VideoSchedule(Base):
    __tablename__ = "video_schedules"

    __table_args__ = (
        Index("ix_video_schedules_video_id", "video_id"),
        CheckConstraint("start_time <= end_time", name="check_schedule_time_range"),
    )

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    status = Column(String(20), default="active", nullable=False)
    description = Column(String(500))

    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    video = relationship("Video", back_populates="schedules")
