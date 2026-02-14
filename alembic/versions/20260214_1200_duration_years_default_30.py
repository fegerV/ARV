"""Change duration_years default to 30, relax check constraint.

Revision ID: 20260214_1200_dur30
Revises: 20260213_1200_yd_storage
Create Date: 2026-02-14 12:00:00

All new AR content gets 30-year (effectively permanent) access.
Old rows with 1/3/5 years are updated to 30.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260214_1200_dur30"
down_revision: Union[str, None] = "20260213_1200_yd_storage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old constraint (only allows 1, 3, 5)
    try:
        op.drop_constraint("check_duration_years", "ar_content", type_="check")
    except Exception:
        pass  # Constraint may not exist (e.g. fresh DB)

    # Create a relaxed constraint (>= 1)
    try:
        op.create_check_constraint(
            "check_duration_years",
            "ar_content",
            "duration_years >= 1",
        )
    except Exception:
        pass

    # Change column default to 30
    try:
        op.alter_column(
            "ar_content",
            "duration_years",
            server_default=sa.text("30"),
        )
    except Exception:
        pass

    # Update existing rows that have old defaults (1, 3, 5) to 30
    op.execute("UPDATE ar_content SET duration_years = 30 WHERE duration_years IN (1, 3, 5)")


def downgrade() -> None:
    op.execute("UPDATE ar_content SET duration_years = 1 WHERE duration_years = 30")
    try:
        op.drop_constraint("check_duration_years", "ar_content", type_="check")
    except Exception:
        pass
    try:
        op.create_check_constraint(
            "check_duration_years",
            "ar_content",
            "duration_years IN (1, 3, 5)",
        )
    except Exception:
        pass
    try:
        op.alter_column(
            "ar_content",
            "duration_years",
            server_default=sa.text("1"),
        )
    except Exception:
        pass
