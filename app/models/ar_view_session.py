from sqlalchemy import Column, Index, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid
from datetime import datetime


class ARViewSession(Base):
    __tablename__ = "ar_view_sessions"

    __table_args__ = (
        Index("ix_ar_view_sessions_created_at", "created_at"),
        Index("ix_ar_view_sessions_company_id", "company_id"),
        Index("ix_ar_view_sessions_project_id", "project_id"),
        Index("ix_ar_view_sessions_ar_content_id", "ar_content_id"),
    )

    # Use Integer as primary key to match migration
    id = Column(Integer, primary_key=True, index=True)
    
    ar_content_id = Column(Integer, ForeignKey("ar_content.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    # Use String for SQLite compatibility, UUID for PostgreSQL
    session_id = Column(String(36), nullable=False)  # Store UUID as string for SQLite compatibility

    user_agent = Column(String)
    device_type = Column(String(50))
    browser = Column(String(100))
    os = Column(String(100))

    ip_address = Column(String(64))
    country = Column(String(100))
    city = Column(String(100))

    duration_seconds = Column(Integer)
    tracking_quality = Column(String(50))
    video_played = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    ar_content = relationship("ARContent")
    project = relationship("Project")
    company = relationship("Company")