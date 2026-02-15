"""Notification model for system/email/telegram alerts."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Notification(Base):
    __tablename__ = "notifications"

    __table_args__ = (
        Index("ix_notifications_company_id", "company_id"),
        Index("ix_notifications_created_at", "created_at"),
        Index("ix_notifications_type", "notification_type"),
    )

    id = Column(Integer, primary_key=True)

    # Foreign keys with referential integrity
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    ar_content_id = Column(Integer, ForeignKey("ar_content.id"), nullable=True)

    notification_type = Column(String(50), nullable=False)

    email_sent = Column(Boolean, default=False, nullable=False)
    email_sent_at = Column(DateTime)
    email_error = Column(Text)

    telegram_sent = Column(Boolean, default=False, nullable=False)
    telegram_sent_at = Column(DateTime)
    telegram_error = Column(Text)

    subject = Column(String(500))
    message = Column(Text)

    notification_metadata = Column("metadata", JSON().with_variant(JSONB, "postgresql"), default={})

    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
