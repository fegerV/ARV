"""extend video_rotation_schedule with new fields

Revision ID: 20260127_1300_extend_rotation
Revises: 20260127_1200_add_rotation_state
Create Date: 2025-01-27 13:00:00.000000

PostgreSQL: ADD COLUMN IF NOT EXISTS. SQLite: conditional add via PRAGMA table_info.
"""
from typing import Sequence, Union
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '20260127_1300_extend_rotation'
down_revision: Union[str, None] = '20260127_1200_add_rotation_state'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_columns_sqlite(conn, table: str) -> set[str]:
    """Return set of column names in table (SQLite)."""
    result = conn.execute(text(f"PRAGMA table_info({table})"))
    return {row[1] for row in result}


def upgrade() -> None:
    """Add new fields to video_rotation_schedules (idempotent)."""
    conn = op.get_bind()

    columns_pg = [
        "ALTER TABLE video_rotation_schedules ADD COLUMN IF NOT EXISTS default_video_id INTEGER",
        "ALTER TABLE video_rotation_schedules ADD COLUMN IF NOT EXISTS date_rules JSONB",
        "ALTER TABLE video_rotation_schedules ADD COLUMN IF NOT EXISTS random_seed VARCHAR(32)",
        "ALTER TABLE video_rotation_schedules ADD COLUMN IF NOT EXISTS no_repeat_days INTEGER DEFAULT 1",
        "ALTER TABLE video_rotation_schedules ADD COLUMN IF NOT EXISTS next_change_at TIMESTAMP",
        "ALTER TABLE video_rotation_schedules ADD COLUMN IF NOT EXISTS last_changed_at TIMESTAMP",
        "ALTER TABLE video_rotation_schedules ADD COLUMN IF NOT EXISTS notify_before_expiry_days INTEGER DEFAULT 7",
    ]
    columns_sqlite = [
        ("default_video_id", "INTEGER"),
        ("date_rules", "TEXT"),  # SQLite: JSON as TEXT
        ("random_seed", "VARCHAR(32)"),
        ("no_repeat_days", "INTEGER DEFAULT 1"),
        ("next_change_at", "TIMESTAMP"),
        ("last_changed_at", "TIMESTAMP"),
        ("notify_before_expiry_days", "INTEGER DEFAULT 7"),
    ]

    if conn.dialect.name == 'postgresql':
        for sql in columns_pg:
            op.execute(sql)
        op.execute("""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_video_rotation_schedules_default_video') THEN
                    ALTER TABLE video_rotation_schedules
                    ADD CONSTRAINT fk_video_rotation_schedules_default_video
                    FOREIGN KEY (default_video_id) REFERENCES videos(id);
                END IF;
            END $$
        """)
    else:
        existing = _existing_columns_sqlite(conn, "video_rotation_schedules")
        for col_name, col_type in columns_sqlite:
            if col_name not in existing:
                op.execute(
                    f"ALTER TABLE video_rotation_schedules ADD COLUMN {col_name} {col_type}"
                )


def downgrade() -> None:
    """Remove new fields from video_rotation_schedules table."""
    conn = op.get_bind()
    try:
        if conn.dialect.name == 'postgresql':
            op.drop_constraint(
                'fk_video_rotation_schedules_default_video',
                'video_rotation_schedules',
                type_='foreignkey',
            )
        op.drop_column('video_rotation_schedules', 'default_video_id')
    except Exception:
        pass
    
    try:
        op.drop_column('video_rotation_schedules', 'date_rules')
    except Exception:
        pass
    
    try:
        op.drop_column('video_rotation_schedules', 'random_seed')
    except Exception:
        pass
    
    try:
        op.drop_column('video_rotation_schedules', 'no_repeat_days')
    except Exception:
        pass
    
    try:
        op.drop_column('video_rotation_schedules', 'next_change_at')
    except Exception:
        pass
    
    try:
        op.alter_column('video_rotation_schedules', 'last_changed_at',
            new_column_name='last_rotation_at')
    except Exception:
        pass
    
    try:
        op.drop_column('video_rotation_schedules', 'notify_before_expiry_days')
    except Exception:
        pass
