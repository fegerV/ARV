"""extend video_rotation_schedule with new fields

Revision ID: 20260127_1300_extend_rotation
Revises: 20260127_1200_add_rotation_state
Create Date: 2025-01-27 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260127_1300_extend_rotation'
down_revision: Union[str, None] = '20260127_1200_add_rotation_state'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new fields to video_rotation_schedules table"""
    try:
        # Add default_video_id
        op.add_column('video_rotation_schedules',
            sa.Column('default_video_id', sa.Integer(), nullable=True))
        op.create_foreign_key(
            'fk_video_rotation_schedules_default_video',
            'video_rotation_schedules', 'videos',
            ['default_video_id'], ['id']
        )
    except Exception:
        pass
    
    try:
        # Add date_rules (JSONB for PostgreSQL, JSON for SQLite)
        op.add_column('video_rotation_schedules',
            sa.Column('date_rules', 
                sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'),
                nullable=True))
    except Exception:
        pass
    
    try:
        # Add random_seed
        op.add_column('video_rotation_schedules',
            sa.Column('random_seed', sa.String(length=32), nullable=True))
    except Exception:
        pass
    
    try:
        # Add no_repeat_days
        op.add_column('video_rotation_schedules',
            sa.Column('no_repeat_days', sa.Integer(), nullable=True, server_default='1'))
    except Exception:
        pass
    
    try:
        # Add next_change_at
        op.add_column('video_rotation_schedules',
            sa.Column('next_change_at', sa.DateTime(), nullable=True))
    except Exception:
        pass
    
    try:
        # Add last_changed_at (rename from last_rotation_at if exists)
        try:
            op.alter_column('video_rotation_schedules', 'last_rotation_at',
                new_column_name='last_changed_at')
        except Exception:
            # Column might not exist, add new one
            op.add_column('video_rotation_schedules',
                sa.Column('last_changed_at', sa.DateTime(), nullable=True))
    except Exception:
        pass
    
    try:
        # Add notify_before_expiry_days
        op.add_column('video_rotation_schedules',
            sa.Column('notify_before_expiry_days', sa.Integer(), nullable=True, server_default='7'))
    except Exception:
        pass
    
    try:
        # Change is_active from Integer to Boolean
        # First, create new column
        op.add_column('video_rotation_schedules',
            sa.Column('is_active_new', sa.Boolean(), nullable=True, server_default='true'))
        # Copy data
        op.execute("UPDATE video_rotation_schedules SET is_active_new = (is_active = 1)")
        # Drop old column
        op.drop_column('video_rotation_schedules', 'is_active')
        # Rename new column
        op.alter_column('video_rotation_schedules', 'is_active_new',
            new_column_name='is_active')
    except Exception:
        # If conversion fails, just ensure column exists
        try:
            op.add_column('video_rotation_schedules',
                sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'))
        except Exception:
            pass


def downgrade() -> None:
    """Remove new fields from video_rotation_schedules table"""
    try:
        op.drop_constraint('fk_video_rotation_schedules_default_video', 
            'video_rotation_schedules', type_='foreignkey')
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
