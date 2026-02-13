"""Add storage_provider and yandex_disk_token columns to companies

Revision ID: 20260213_1200_yd_storage
Revises: 20260211_1200_vs_datetime
Create Date: 2026-02-13 12:00:00

Adds pluggable storage provider support: each company can use local or Yandex Disk storage.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "20260213_1200_yd_storage"
down_revision: Union[str, None] = "20260211_1200_vs_datetime"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column(
            "storage_provider",
            sa.String(50),
            nullable=False,
            server_default="local",
        ),
    )
    op.add_column(
        "companies",
        sa.Column("yandex_disk_token", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("companies", "yandex_disk_token")
    op.drop_column("companies", "storage_provider")
