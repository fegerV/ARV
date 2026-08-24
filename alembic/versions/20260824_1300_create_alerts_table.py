"""Create alerts table for system alert persistence.

Revision ID: 20260824_1300_create_alerts_table
Revises: 20260821_1245_backup_checksum
Create Date: 2026-08-24 13:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260824_1300_create_alerts_table"
down_revision: Union[str, None] = "20260821_1245_backup_checksum"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("affected_services", sa.JSON(), nullable=True),
        sa.Column("acknowledged", sa.Boolean(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("acknowledged_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"], unique=False)
    op.create_index("ix_alerts_severity", "alerts", ["severity"], unique=False)
    op.create_index("ix_alerts_acknowledged", "alerts", ["acknowledged"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_alerts_acknowledged", table_name="alerts")
    op.drop_index("ix_alerts_severity", table_name="alerts")
    op.drop_index("ix_alerts_created_at", table_name="alerts")
    op.drop_table("alerts")
