"""Add device_model to ar_view_sessions for analytics (Android/iOS models).

Revision ID: 20260219_1000_devmodel
Revises: 20260215_1200_dedup
Create Date: 2026-02-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260219_1000_devmodel"
down_revision: Union[str, None] = "20260215_1200_dedup"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ar_view_sessions",
        sa.Column("device_model", sa.String(120), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ar_view_sessions", "device_model")
