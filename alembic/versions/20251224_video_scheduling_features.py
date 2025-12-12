"""Add video scheduling and rotation features

This migration adds:
- video_schedules table for time-based video scheduling
- subscription_end field to videos table for access control
- rotation_state field to ar_content table for rotation tracking
- Updates rotation_type to only allow 'none', 'sequential', 'cyclic'

Revision ID: 20251224_video_scheduling_features
Revises: 20251223_schema_migration_overhaul
Create Date: 2025-12-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20251224_video_scheduling_features'
down_revision = '20251223_schema_migration_overhaul'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create video_schedules table
    op.create_table('video_schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('start_time <= end_time', name='check_schedule_time_range')
    )
    op.create_index(op.f('ix_video_schedules_video_id'), 'video_schedules', ['video_id'], unique=False)
    
    # 2. Add subscription_end to videos table
    op.add_column('videos', sa.Column('subscription_end', sa.DateTime(), nullable=True))
    
    # 3. Add rotation_state to ar_content table
    op.add_column('ar_content', sa.Column('rotation_state', sa.Integer(), nullable=True, server_default='0'))
    
    # 4. Update rotation_type column constraints and default values
    # First, update any existing values to be valid
    op.execute("UPDATE videos SET rotation_type = 'none' WHERE rotation_type NOT IN ('none', 'sequential', 'cyclic')")
    
    # Add check constraint for rotation_type
    op.create_check_constraint(
        'check_video_rotation_type', 
        'videos', 
        "rotation_type IN ('none', 'sequential', 'cyclic')"
    )


def downgrade() -> None:
    # 1. Remove check constraint for rotation_type
    op.drop_constraint('check_video_rotation_type', 'videos', type_='check')
    
    # 2. Remove rotation_state from ar_content
    op.drop_column('ar_content', 'rotation_state')
    
    # 3. Remove subscription_end from videos
    op.drop_column('videos', 'subscription_end')
    
    # 4. Drop video_schedules table
    op.drop_index(op.f('ix_video_schedules_video_id'), table_name='video_schedules')
    op.drop_table('video_schedules')