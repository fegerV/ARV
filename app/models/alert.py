"""Alert model for system alerts persistence."""

from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Alert(Base):
    __tablename__ = "alerts"

    __table_args__ = (
        Index("ix_alerts_created_at", "created_at"),
        Index("ix_alerts_severity", "severity"),
        Index("ix_alerts_acknowledged", "acknowledged"),
    )

    id = Column(Integer, primary_key=True)
    severity = Column(String(20), nullable=False)
    title = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    metrics = Column(JSON().with_variant(JSONB, "postgresql"), default={})
    affected_services = Column(JSON().with_variant(JSONB, "postgresql"), default=[])
    acknowledged = Column(Boolean, default=False, nullable=False)
    acknowledged_at = Column(DateTime)
    acknowledged_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
