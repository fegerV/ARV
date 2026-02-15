"""Email queue model for outgoing emails."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EmailQueue(Base):
    __tablename__ = "email_queue"

    __table_args__ = (
        Index("ix_email_queue_status", "status"),
        Index("ix_email_queue_scheduled_at", "scheduled_at"),
        Index("ix_email_queue_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True)

    recipient_to = Column(String(255), nullable=False)
    recipient_cc = Column(String(255))
    recipient_bcc = Column(String(255))
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    html = Column(Text)

    template_id = Column(String(100))
    variables = Column(JSON().with_variant(JSONB, "postgresql"), default={})

    status = Column(String(50), default="pending", nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)

    last_error = Column(Text)

    priority = Column(Integer, default=5, nullable=False)
    scheduled_at = Column(DateTime)

    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
    sent_at = Column(DateTime)
