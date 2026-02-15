"""Backup history model for tracking database backups."""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class BackupHistory(Base):
    """Record of a single database backup attempt."""

    __tablename__ = "backup_history"

    __table_args__ = (
        Index("ix_backup_history_company_id", "company_id"),
        Index("ix_backup_history_started_at", "started_at"),
    )

    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, nullable=False, default=_utcnow)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="running")
    size_bytes = Column(BigInteger, nullable=True)
    yd_path = Column(String(500), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    error_message = Column(Text, nullable=True)
    trigger = Column(String(20), nullable=False, default="manual")
