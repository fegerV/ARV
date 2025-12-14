"""Add missing fields to ar_content table

Revision ID: 20250624_add_ar_content_fields
Revises: 20251223_schema_migration_overhaul
Create Date: 2025-06-24 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20250624_add_ar_content_fields'
down_revision: Union[str, None] = '20251223_schema_migration_overhaul'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing fields to ar_content table."""
    
    # Add unique_id column with UUID type and default
    op.add_column('ar_contents', sa.Column('unique_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')))
    
    # Add file storage columns
    op.add_column('ar_contents', sa.Column('photo_path', sa.String(length=500), nullable=True))
    op.add_column('ar_contents', sa.Column('photo_url', sa.String(length=500), nullable=True))
    op.add_column('ar_contents', sa.Column('video_path', sa.String(length=500), nullable=True))
    op.add_column('ar_contents', sa.Column('video_url', sa.String(length=500), nullable=True))
    op.add_column('ar_contents', sa.Column('qr_code_path', sa.String(length=500), nullable=True))
    op.add_column('ar_contents', sa.Column('qr_code_url', sa.String(length=500), nullable=True))
    
    # Create unique index on unique_id
    op.create_index('ix_ar_content_unique_id', 'ar_contents', ['unique_id'], unique=True)
    
    # Populate unique_id for existing records using their id
    op.execute("""
        UPDATE ar_contents 
        SET unique_id = id::uuid 
        WHERE unique_id IS NULL
    """)


def downgrade() -> None:
    """Remove the added fields."""
    
    # Drop indexes
    op.drop_index('ix_ar_content_unique_id', table_name='ar_contents')
    
    # Drop columns
    op.drop_column('ar_contents', 'qr_code_url')
    op.drop_column('ar_contents', 'qr_code_path')
    op.drop_column('ar_contents', 'video_url')
    op.drop_column('ar_contents', 'video_path')
    op.drop_column('ar_contents', 'photo_url')
    op.drop_column('ar_contents', 'photo_path')
    op.drop_column('ar_contents', 'unique_id')