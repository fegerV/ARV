"""AR view session model for analytics."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ARViewSession(Base):
    __tablename__ = "ar_view_sessions"

    __table_args__ = (
        Index("ix_ar_view_sessions_created_at", "created_at"),
        Index("ix_ar_view_sessions_company_id", "company_id"),
        Index("ix_ar_view_sessions_project_id", "project_id"),
        Index("ix_ar_view_sessions_ar_content_id", "ar_content_id"),
    )

    id = Column(Integer, primary_key=True)

    ar_content_id = Column(Integer, ForeignKey("ar_content.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)

    session_id = Column(String(36), nullable=False)

    user_agent = Column(String)
    device_type = Column(String(50))
    browser = Column(String(100))
    os = Column(String(100))

    ip_address = Column(String(64))
    country = Column(String(100))
    city = Column(String(100))

    duration_seconds = Column(Integer)
    tracking_quality = Column(String(50))
    video_played = Column(Boolean, default=False, server_default="false", nullable=False)

    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    ar_content = relationship("ARContent")
    project = relationship("Project")
    company = relationship("Company")
