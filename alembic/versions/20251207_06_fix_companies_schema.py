"""Fix companies schema to match model definition

Revision ID: 20251207_06_fix_companies_schema
Revises: 20251207_05_fix_storage_connections_schema
Create Date: 2025-12-07 17:50:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20251207_06_fix_companies_schema"
down_revision = "20251207_05_fix_storage_connections_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add missing columns to companies table to match the model definition."""
    # Add missing columns
    op.add_column('companies', sa.Column('telegram_chat_id', sa.String(100), nullable=True))
    op.add_column('companies', sa.Column('subscription_tier', sa.String(50), nullable=True))
    op.add_column('companies', sa.Column('projects_limit', sa.Integer(), nullable=True))
    op.add_column('companies', sa.Column('subscription_expires_at', sa.DateTime(), nullable=True))
    op.add_column('companies', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('companies', sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('companies', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('companies', sa.Column('created_by', sa.Integer(), nullable=True))
    
    # Add default values for new columns
    op.execute("UPDATE companies SET subscription_tier = 'basic'")
    op.execute("UPDATE companies SET projects_limit = 50")
    
    # Add indexes if needed
    op.create_index('ix_companies_subscription_tier', 'companies', ['subscription_tier'])
    op.create_index('ix_companies_is_active', 'companies', ['is_active'])


def downgrade() -> None:
    """Remove the added columns from companies table."""
    # Drop indexes
    op.drop_index('ix_companies_is_active', table_name='companies')
    op.drop_index('ix_companies_subscription_tier', table_name='companies')
    
    # Drop columns
    op.drop_column('companies', 'created_by')
    op.drop_column('companies', 'updated_at')
    op.drop_column('companies', 'metadata')
    op.drop_column('companies', 'notes')
    op.drop_column('companies', 'subscription_expires_at')
    op.drop_column('companies', 'projects_limit')
    op.drop_column('companies', 'subscription_tier')
    op.drop_column('companies', 'telegram_chat_id')