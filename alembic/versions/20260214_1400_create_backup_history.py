"""Create backup_history table.

Revision ID: 20260214_1400_bkp
Revises: 20260214_1200_dur30
Create Date: 2026-02-14 14:00:00

Stores the history of database backup operations including status,
file size, Yandex Disk path, and the company whose token was used.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260214_1400_bkp"
down_revision: Union[str, None] = "20260214_1200_dur30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "backup_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("yd_path", sa.String(500), nullable=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("trigger", sa.String(20), nullable=False, server_default="manual"),
    )
    op.create_index("ix_backup_history_company_id", "backup_history", ["company_id"])
    op.create_index("ix_backup_history_started_at", "backup_history", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_backup_history_started_at", table_name="backup_history")
    op.drop_index("ix_backup_history_company_id", table_name="backup_history")
    op.drop_table("backup_history")
