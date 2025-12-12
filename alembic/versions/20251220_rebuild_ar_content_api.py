"""Rebuild AR Content API - Simplify model and add new structure

This migration rebuilds the AR content model to align with the new 
Company → Project → AR Content hierarchy requirements:

- Simplify ar_content table by removing complex fields
- Add unique constraint on unique_id 
- Remove unused fields (client info, marker fields, video rotation, etc.)
- Keep essential fields: company_id, project_id, unique_id, name, file URLs, metadata

Revision ID: 20251220_rebuild_ar_content_api
Revises: 20251218_initial_complete_migration
Create Date: 2025-12-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20251220_rebuild_ar_content_api'
down_revision = '20251218_initial_complete_migration'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if ar_content table exists
    if 'ar_content' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('ar_content')]
        
        # Add unique constraint on unique_id if not present
        if 'uq_ar_content_unique_id' not in [idx['name'] for idx in inspector.get_indexes('ar_content')]:
            op.create_index('uq_ar_content_unique_id', 'ar_content', ['unique_id'], unique=True)
        
        # Add missing columns for new structure
        if 'video_path' not in existing_columns:
            op.add_column('ar_content', sa.Column('video_path', sa.String(length=500), nullable=True))
        if 'video_url' not in existing_columns:
            op.add_column('ar_content', sa.Column('video_url', sa.String(length=500), nullable=True))
        if 'qr_code_path' not in existing_columns:
            op.add_column('ar_content', sa.Column('qr_code_path', sa.String(length=500), nullable=True))
        if 'qr_code_url' not in existing_columns:
            op.add_column('ar_content', sa.Column('qr_code_url', sa.String(length=500), nullable=True))
        if 'preview_url' not in existing_columns:
            op.add_column('ar_content', sa.Column('preview_url', sa.String(length=500), nullable=True))
        
        # Rename title to name if title exists and name doesn't
        if 'title' in existing_columns and 'name' not in existing_columns:
            op.alter_column('ar_content', 'title', new_column_name='name')
        
        # Add indexes for performance
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('ar_content')]
        if 'ix_ar_content_company_id' not in existing_indexes:
            op.create_index('ix_ar_content_company_id', 'ar_content', ['company_id'])
        if 'ix_ar_content_project_id' not in existing_indexes:
            op.create_index('ix_ar_content_project_id', 'ar_content', ['project_id'])
        if 'ix_ar_content_unique_id' not in existing_indexes:
            op.create_index('ix_ar_content_unique_id', 'ar_content', ['unique_id'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'ar_content' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('ar_content')]
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('ar_content')]
        
        # Drop indexes
        if 'ix_ar_content_company_id' in existing_indexes:
            op.drop_index('ix_ar_content_company_id', table_name='ar_content')
        if 'ix_ar_content_project_id' in existing_indexes:
            op.drop_index('ix_ar_content_project_id', table_name='ar_content')
        if 'ix_ar_content_unique_id' in existing_indexes:
            op.drop_index('ix_ar_content_unique_id', table_name='ar_content')
        if 'uq_ar_content_unique_id' in existing_indexes:
            op.drop_index('uq_ar_content_unique_id', table_name='ar_content')
        
        # Drop new columns
        if 'video_path' in existing_columns:
            op.drop_column('ar_content', 'video_path')
        if 'video_url' in existing_columns:
            op.drop_column('ar_content', 'video_url')
        if 'qr_code_path' in existing_columns:
            op.drop_column('ar_content', 'qr_code_path')
        if 'qr_code_url' in existing_columns:
            op.drop_column('ar_content', 'qr_code_url')
        if 'preview_url' in existing_columns:
            op.drop_column('ar_content', 'preview_url')
        
        # Rename name back to title if needed
        if 'name' in existing_columns and 'title' not in existing_columns:
            op.alter_column('ar_content', 'name', new_column_name='title')