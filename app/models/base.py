"""Abstract base model (currently unused — kept for potential future use)."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base

import uuid


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BaseModel(Base):
    """Abstract base model with common timestamp fields."""

    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
