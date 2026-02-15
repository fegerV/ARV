"""Video model."""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.enums import VideoStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Video(Base):
    __tablename__ = "videos"

    __table_args__ = (
        Index("ix_videos_ar_content_id", "ar_content_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    ar_content_id = Column(Integer, ForeignKey("ar_content.id"), nullable=False)

    # File information
    filename = Column(String(255), nullable=False)
    video_path = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)
    thumbnail_path = Column(String(500), nullable=True)
    preview_url = Column(String(500), nullable=True)

    # Video metadata
    duration = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    size_bytes = Column(BigInteger)  # BigInteger supports files > 2 GB
    mime_type = Column(String(100))

    # Status
    status = Column(String(50), default=VideoStatus.UPLOADED, nullable=False)

    # Playback/rotation
    is_active = Column(Boolean, default=False, nullable=False)
    rotation_type = Column(String(20), default="none", nullable=False)
    rotation_order = Column(Integer, default=0, nullable=False)
    rotation_weight = Column(Integer, default=1, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    subscription_end = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    ar_content = relationship("ARContent", back_populates="videos", foreign_keys=[ar_content_id])
    schedules = relationship("VideoSchedule", back_populates="video", cascade="all, delete-orphan")
