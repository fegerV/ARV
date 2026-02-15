"""Audit log model for tracking entity changes."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_actor_id", "actor_id"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True)

    entity_type = Column(String(100), nullable=False)
    entity_id = Column(Integer, nullable=False)

    action = Column(String(100), nullable=False)

    changes = Column(JSON().with_variant(JSONB, "postgresql"), default={})
    field_name = Column(String(100))

    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_email = Column(String(255))
    actor_ip = Column(String(64))
    user_agent = Column(Text)

    session_id = Column(String(255))
    request_id = Column(String(255))

    created_at = Column(DateTime, default=_utcnow, nullable=False)

    # Relationships
    actor = relationship("User", foreign_keys=[actor_id])
