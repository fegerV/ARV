"""Backup history model for tracking database, media and config backups."""

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class BackupHistory(Base):
    """Record of a single backup attempt.

    Beyond the basic outcome this row is the operational source of truth for
    monitoring: ``verified_at`` / ``restore_tested_at`` answer "can we actually
    restore this?" and ``app_commit`` records which application revision the
    dump corresponds to (see docs/BACKUP_AND_RECOVERY.md).
    """

    __tablename__ = "backup_history"

    __table_args__ = (
        Index("ix_backup_history_company_id", "company_id"),
        Index("ix_backup_history_started_at", "started_at"),
        Index("ix_backup_history_backup_type", "backup_type"),
    )

    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, nullable=False, default=_utcnow)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="running")
    size_bytes = Column(BigInteger, nullable=True)
    checksum = Column(String(64), nullable=True)
    yd_path = Column(String(500), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    error_message = Column(Text, nullable=True)
    trigger = Column(String(20), nullable=False, default="manual")

    # --- classification -------------------------------------------------
    # ``db`` | ``media`` | ``secrets`` | ``config``
    backup_type = Column(String(20), nullable=False, default="db")
    # ``primary`` | ``secondary`` | ``offline`` | ``local``
    target = Column(String(20), nullable=True)
    encrypted = Column(Boolean, nullable=False, default=False)
    duration_seconds = Column(Integer, nullable=True)
    # Application revision the backup corresponds to, so a restore can be
    # performed against a compatible schema.
    app_commit = Column(String(40), nullable=True)

    # --- verification ---------------------------------------------------
    verified_at = Column(DateTime, nullable=True)
    # ``ok`` | ``checksum_mismatch`` | ``restore_failed`` | ``pending``
    verification_status = Column(String(30), nullable=True)
    restore_tested_at = Column(DateTime, nullable=True)
    restore_test_status = Column(String(30), nullable=True)
    # Remote paths for the additional copies (primary stays in ``yd_path``).
    secondary_path = Column(String(500), nullable=True)
    snapshot_id = Column(String(120), nullable=True)

