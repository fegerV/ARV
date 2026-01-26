"""Add missing columns to folders table

Revision ID: 20260125_1203_add_missing_columns_to_folders
Revises: 20260125_1202_add_project_id_to_folders
Create Date: 2026-01-25 12:03:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260125_1203_add_missing_columns_to_folders'
down_revision = '20260125_1202_add_project_id_to_folders'
branch_labels = None
depends_on = None


def upgrade():
    """Add missing columns to folders table."""
    # Check if columns already exist (for safety)
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('folders')]
    
    # Add description column if it doesn't exist
    if 'description' not in columns:
        op.add_column('folders', 
                     sa.Column('description', sa.Text(), nullable=True))
    
    # Add folder_path column if it doesn't exist (note: there's already 'path' column)
    if 'folder_path' not in columns:
        op.add_column('folders', 
                     sa.Column('folder_path', sa.String(length=500), nullable=True))
    
    # Add is_active column if it doesn't exist
    if 'is_active' not in columns:
        op.add_column('folders', 
                     sa.Column('is_active', sa.String(length=50), nullable=True, server_default='active'))
    
    # Add sort_order column if it doesn't exist
    if 'sort_order' not in columns:
        op.add_column('folders', 
                     sa.Column('sort_order', sa.Integer(), nullable=True, server_default='0'))


def downgrade():
    """Remove added columns from folders table."""
    # Check if columns exist before dropping
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('folders')]
    
    if 'sort_order' in columns:
        op.drop_column('folders', 'sort_order')
    
    if 'is_active' in columns:
        op.drop_column('folders', 'is_active')
    
    if 'folder_path' in columns:
        op.drop_column('folders', 'folder_path')
    
    if 'description' in columns:
        op.drop_column('folders', 'description')
