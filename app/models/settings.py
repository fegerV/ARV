"""System settings model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, String, Text

from app.core.database import Base


def _utcnow() -> datetime:
    """Timezone-aware UTC now (replacement for deprecated datetime.utcnow)."""
    return datetime.now(timezone.utc)


class SystemSettings(Base):
    """Key-value system settings stored in the database."""

    __tablename__ = "system_settings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    data_type = Column(String(20), default="string", nullable=False)
    category = Column(String(50), default="general", nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<SystemSettings(key='{self.key}', category='{self.category}')>"
