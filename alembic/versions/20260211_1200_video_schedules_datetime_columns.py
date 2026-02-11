"""Convert video_schedules start_time and end_time from VARCHAR to TIMESTAMP

Revision ID: 20260211_1200_vs_datetime
Revises: 20260202_1400_rotation_type
Create Date: 2026-02-11 12:00:00

Fixes: operator does not exist: character varying <= timestamp without time zone
The initial schema created start_time/end_time as String(8); the model expects DateTime.
"""
from typing import Sequence, Union
from alembic import op

revision: str = "20260211_1200_vs_datetime"
down_revision: Union[str, None] = "20260202_1400_rotation_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert start_time and end_time to TIMESTAMP (PostgreSQL)."""
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    # Support both 8-char YYYYMMDD and ISO-style strings
    op.execute(
        "ALTER TABLE video_schedules "
        "ALTER COLUMN start_time TYPE TIMESTAMP WITH TIME ZONE USING "
        "(CASE WHEN length(start_time) = 8 AND start_time ~ '^\\d{8}$' "
        "THEN to_timestamp(start_time, 'YYYYMMDD') AT TIME ZONE 'UTC' "
        "ELSE start_time::timestamptz END)"
    )
    op.execute(
        "ALTER TABLE video_schedules "
        "ALTER COLUMN end_time TYPE TIMESTAMP WITH TIME ZONE USING "
        "(CASE WHEN length(end_time) = 8 AND end_time ~ '^\\d{8}$' "
        "THEN to_timestamp(end_time, 'YYYYMMDD') AT TIME ZONE 'UTC' "
        "ELSE end_time::timestamptz END)"
    )


def downgrade() -> None:
    """Revert to VARCHAR(50) to hold ISO strings (lossy)."""
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.execute(
        "ALTER TABLE video_schedules "
        "ALTER COLUMN start_time TYPE VARCHAR(50) USING start_time::text"
    )
    op.execute(
        "ALTER TABLE video_schedules "
        "ALTER COLUMN end_time TYPE VARCHAR(50) USING end_time::text"
    )
