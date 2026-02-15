"""Project model."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.enums import ProjectStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    """Project model with relationships to Company and AR Content."""

    __tablename__ = "projects"

    __table_args__ = (
        Index("ix_project_company_name", "company_id", "name"),
    )

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    status = Column(String(50), default=ProjectStatus.ACTIVE, nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)

    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    company = relationship("Company", back_populates="projects")
    ar_contents = relationship("ARContent", back_populates="project", cascade="all, delete-orphan")

    # NOTE: ar_content_count property removed — lazy-load unsafe in async.
    # Use COUNT query in route/service layer.

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name} status={self.status}>"
