"""Add rotation_type and missing columns to video_rotation_schedules (SQLite compatibility).

Revision ID: 20260202_1400_rotation_type
Revises: 20260127_1310_add_video_fields
Create Date: 2026-02-02 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "20260202_1400_rotation_type"
down_revision: Union[str, None] = "20260127_1310_add_video_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add rotation_type and other columns expected by VideoRotationSchedule model."""
    # rotation_type (table had schedule_type from initial schema; model expects rotation_type)
    try:
        op.add_column(
            "video_rotation_schedules",
            sa.Column("rotation_type", sa.String(length=50), nullable=True, server_default="fixed"),
        )
    except Exception:
        pass

    # video_sequence (JSON)
    try:
        op.add_column(
            "video_rotation_schedules",
            sa.Column("video_sequence", sa.JSON(), nullable=True),
        )
    except Exception:
        pass

    # current_index
    try:
        op.add_column(
            "video_rotation_schedules",
            sa.Column("current_index", sa.Integer(), nullable=True, server_default="0"),
        )
    except Exception:
        pass

    # cron_expression
    try:
        op.add_column(
            "video_rotation_schedules",
            sa.Column("cron_expression", sa.String(length=100), nullable=True),
        )
    except Exception:
        pass

    # time_of_day
    try:
        op.add_column(
            "video_rotation_schedules",
            sa.Column("time_of_day", sa.Time(), nullable=True),
        )
    except Exception:
        pass

    # day_of_week
    try:
        op.add_column(
            "video_rotation_schedules",
            sa.Column("day_of_week", sa.Integer(), nullable=True),
        )
    except Exception:
        pass

    # day_of_month
    try:
        op.add_column(
            "video_rotation_schedules",
            sa.Column("day_of_month", sa.Integer(), nullable=True),
        )
    except Exception:
        pass


def downgrade() -> None:
    """Remove added columns."""
    for col in ("day_of_month", "day_of_week", "time_of_day", "cron_expression", "current_index", "video_sequence", "rotation_type"):
        try:
            op.drop_column("video_rotation_schedules", col)
        except Exception:
            pass
