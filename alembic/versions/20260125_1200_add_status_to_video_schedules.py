"""Add status column to video_schedules table

Revision ID: 20260125_1200_add_status_to_video_schedules
Revises: 20251227_1000_create_system_settings
Create Date: 2026-01-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260125_1200_add_status_to_video_schedules'
down_revision = '20251227_1000_create_system_settings'
branch_labels = None
depends_on = None


def upgrade():
    """Add status column to video_schedules table."""
    # Check if column already exists (for safety)
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('video_schedules')]
    
    if 'status' not in columns:
        # SQLite doesn't support ALTER COLUMN for changing nullable
        # So we add column as nullable with default, then update values
        op.add_column('video_schedules', 
                     sa.Column('status', sa.String(length=20), nullable=True, server_default='active'))
        
        # Update existing rows to have 'active' status
        op.execute(
            sa.text("UPDATE video_schedules SET status = 'active' WHERE status IS NULL")
        )
        
        # For SQLite, we can't change nullable after creation, so leave it nullable
        # The default value will handle new rows


def downgrade():
    """Remove status column from video_schedules table."""
    # Check if column exists before dropping
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('video_schedules')]
    
    if 'status' in columns:
        op.drop_column('video_schedules', 'status')
