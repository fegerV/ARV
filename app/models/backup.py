"""Backup history model for tracking database backups."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)

from app.core.database import Base


class BackupHistory(Base):
    """Record of a single database backup attempt.

    Each row tracks when a backup was started, its outcome, file size,
    where it was stored on Yandex Disk, and which company's token was
    used for the upload.
    """

    __tablename__ = "backup_history"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="running")
    size_bytes = Column(BigInteger, nullable=True)
    yd_path = Column(String(500), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    error_message = Column(Text, nullable=True)
    trigger = Column(String(20), nullable=False, default="manual")
