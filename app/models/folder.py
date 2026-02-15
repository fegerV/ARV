"""Folder model (hierarchical project structure)."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Folder(Base):
    __tablename__ = "folders"

    __table_args__ = (
        Index("ix_folders_project_id", "project_id"),
        Index("ix_folders_parent_id", "parent_id"),
    )

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    name = Column(String(255), nullable=False)
    description = Column(Text)

    parent_id = Column(Integer, ForeignKey("folders.id"), nullable=True)
    folder_path = Column(String(500))

    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    project = relationship("Project", backref="folders")
    parent = relationship("Folder", remote_side=[id], backref="children")
