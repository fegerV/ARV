"""Add project_id column to folders table

Revision ID: 20260125_1202_add_project_id_to_folders
Revises: 20260125_1201_add_description_to_video_schedules
Create Date: 2026-01-25 12:02:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260125_1202_add_project_id_to_folders'
down_revision = '20260125_1201_add_description_to_video_schedules'
branch_labels = None
depends_on = None


def upgrade():
    """Add project_id column to folders table."""
    # Check if column already exists (for safety)
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('folders')]
    
    if 'project_id' not in columns:
        # SQLite doesn't support ALTER for foreign keys, so we just add the column
        # The foreign key will be enforced by SQLAlchemy at the application level
        op.add_column('folders', 
                     sa.Column('project_id', sa.Integer(), nullable=True))
        
        # Note: SQLite doesn't support adding foreign key constraints via ALTER
        # The relationship is handled by SQLAlchemy at the application level


def downgrade():
    """Remove project_id column from folders table."""
    # Check if column exists before dropping
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('folders')]
    
    if 'project_id' in columns:
        op.drop_column('folders', 'project_id')
