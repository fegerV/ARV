"""Add missing columns to clients table

Revision ID: 20260125_1204_add_missing_columns_to_clients
Revises: 20260125_1203_add_missing_columns_to_folders
Create Date: 2026-01-25 12:04:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260125_1204_add_missing_columns_to_clients'
down_revision = '20260125_1203_add_missing_columns_to_folders'
branch_labels = None
depends_on = None


def upgrade():
    """Add missing columns to clients table."""
    # Check if columns already exist (for safety)
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('clients')]
    
    # Add address column if it doesn't exist
    if 'address' not in columns:
        op.add_column('clients', 
                     sa.Column('address', sa.String(length=500), nullable=True))
    
    # Add notes column if it doesn't exist
    if 'notes' not in columns:
        op.add_column('clients', 
                     sa.Column('notes', sa.String(length=1000), nullable=True))
    
    # Add is_active column if it doesn't exist
    if 'is_active' not in columns:
        op.add_column('clients', 
                     sa.Column('is_active', sa.String(length=50), nullable=True, server_default='active'))


def downgrade():
    """Remove added columns from clients table."""
    # Check if columns exist before dropping
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('clients')]
    
    if 'is_active' in columns:
        op.drop_column('clients', 'is_active')
    
    if 'notes' in columns:
        op.drop_column('clients', 'notes')
    
    if 'address' in columns:
        op.drop_column('clients', 'address')
