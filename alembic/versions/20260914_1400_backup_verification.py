"""Extend backup_history for media backups, dual targets and verification.

Adds the columns required by the backup/DR design in
docs/BACKUP_AND_RECOVERY.md: backup classification (type, target,
encryption, duration, app revision) and verification tracking
(verified_at, verification_status, restore_tested_at, restore_test_status).

Revision ID: 20260914_1400_backup_verification
Revises: 20260908_1200_create_ai_jobs_table
Create Date: 2026-09-14 14:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260914_1400_backup_verification"
down_revision: Union[str, None] = "20260908_1200_create_ai_jobs_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_COLUMNS: list[tuple[str, sa.types.TypeEngine]] = [
    ("backup_type", sa.String(length=20)),
    ("target", sa.String(length=20)),
    ("encrypted", sa.Boolean()),
    ("duration_seconds", sa.Integer()),
    ("app_commit", sa.String(length=40)),
    ("verified_at", sa.DateTime()),
    ("verification_status", sa.String(length=30)),
    ("restore_tested_at", sa.DateTime()),
    ("restore_test_status", sa.String(length=30)),
    ("secondary_path", sa.String(length=500)),
    ("snapshot_id", sa.String(length=120)),
]


def upgrade() -> None:
    for name, type_ in _COLUMNS:
        if name == "backup_type":
            # Existing rows predate the column and are all database dumps.
            op.add_column(
                "backup_history",
                sa.Column(name, type_, nullable=False, server_default="db"),
            )
        elif name == "encrypted":
            op.add_column(
                "backup_history",
                sa.Column(name, type_, nullable=False, server_default=sa.false()),
            )
        else:
            op.add_column("backup_history", sa.Column(name, type_, nullable=True))

    op.create_index(
        "ix_backup_history_backup_type", "backup_history", ["backup_type"]
    )


def downgrade() -> None:
    op.drop_index("ix_backup_history_backup_type", table_name="backup_history")
    for name, _ in reversed(_COLUMNS):
        op.drop_column("backup_history", name)
