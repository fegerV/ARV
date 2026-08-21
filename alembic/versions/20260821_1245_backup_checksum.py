"""Add checksum column to backup_history for integrity verification.

Revision ID: 20260821_1245_backup_checksum
Revises: 20260821_1230_add_integrity_constraints
Create Date: 2026-08-21 12:45:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260821_1245_backup_checksum"
down_revision: Union[str, None] = "20260821_1230_add_integrity_constraints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("backup_history", sa.Column("checksum", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("backup_history", "checksum")
