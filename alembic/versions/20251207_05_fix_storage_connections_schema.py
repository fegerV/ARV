"""Fix storage_connections schema to match model definition

Revision ID: 20251207_05_fix_storage_connections_schema
Revises: 20251207_04_create_users
Create Date: 2025-12-07 17:45:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20251207_05_fix_storage_connections_schema"
down_revision = "20251207_04_create_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add missing columns to storage_connections table to match the model definition."""
    # Add missing columns
    op.add_column('storage_connections', sa.Column('credentials', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('storage_connections', sa.Column('last_tested_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('storage_connections', sa.Column('test_error', sa.Text(), nullable=True))
    op.add_column('storage_connections', sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('storage_connections', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('storage_connections', sa.Column('created_by', sa.Integer(), nullable=True))
    
    # Add indexes
    op.create_index('ix_storage_connections_provider', 'storage_connections', ['provider'])
    op.create_index('ix_storage_connections_is_active', 'storage_connections', ['is_active'])


def downgrade() -> None:
    """Remove the added columns from storage_connections table."""
    # Drop indexes
    op.drop_index('ix_storage_connections_is_active', table_name='storage_connections')
    op.drop_index('ix_storage_connections_provider', table_name='storage_connections')
    
    # Drop columns
    op.drop_column('storage_connections', 'created_by')
    op.drop_column('storage_connections', 'updated_at')
    op.drop_column('storage_connections', 'metadata')
    op.drop_column('storage_connections', 'test_error')
    op.drop_column('storage_connections', 'last_tested_at')
    op.drop_column('storage_connections', 'credentials')