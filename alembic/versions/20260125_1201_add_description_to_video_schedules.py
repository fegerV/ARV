"""Add description column to video_schedules table

Revision ID: 20260125_1201_add_description_to_video_schedules
Revises: 20260125_1200_add_status_to_video_schedules
Create Date: 2026-01-25 12:01:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260125_1201_add_description_to_video_schedules'
down_revision = '20260125_1200_add_status_to_video_schedules'
branch_labels = None
depends_on = None


def upgrade():
    """Add description column to video_schedules table."""
    # Check if column already exists (for safety)
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('video_schedules')]
    
    if 'description' not in columns:
        # SQLite doesn't support ALTER COLUMN for changing nullable
        # So we add column as nullable (description is optional)
        op.add_column('video_schedules', 
                     sa.Column('description', sa.String(length=500), nullable=True))


def downgrade():
    """Remove description column from video_schedules table."""
    # Check if column exists before dropping
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('video_schedules')]
    
    if 'description' in columns:
        op.drop_column('video_schedules', 'description')
