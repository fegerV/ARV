"""AI Job model for tracking AI processing tasks."""

from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class AIJob(Base):
    """Model representing an AI processing job."""
    
    __tablename__ = "ai_jobs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    ar_content_id: Mapped[int] = mapped_column(Integer, ForeignKey("ar_content.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    
    # Job status and progress
    status: Mapped[str] = mapped_column(String(50), default="queued", nullable=False)  # queued, processing, completed, failed
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0-100
    
    # Model configuration
    model_version: Mapped[str] = mapped_column(String(100), default="default", nullable=False)
    
    # Results
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Audit fields
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    ar_content = relationship("ARContent", back_populates="ai_jobs")
    company = relationship("Company", back_populates="ai_jobs")
    creator = relationship("User", back_populates="ai_jobs_created")
    
    def __repr__(self) -> str:
        return f"<AIJob(id={self.id}, job_id={self.job_id}, status={self.status}, progress={self.progress})>"
