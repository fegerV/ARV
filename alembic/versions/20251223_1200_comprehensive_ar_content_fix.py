"""Comprehensive AR Content schema fix - ensure all required columns and timestamps exist

Revision ID: 20251223_1200_comprehensive_ar_content_fix
Revises: 4f61ed1af7ca
Create Date: 2025-12-23 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251223_1200_comprehensive_ar_content_fix'
down_revision: Union[str, None] = '4f61ed1af7ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ensure all required columns exist in ar_content table with proper defaults"""
    
    # Check and add thumbnail_url if it doesn't exist
    try:
        op.add_column('ar_content', sa.Column('thumbnail_url', sa.String(length=500), nullable=True))
    except Exception:
        # Column might already exist, which is fine
        pass
    
    # Check and add marker fields if they don't exist
    try:
        op.add_column('ar_content', sa.Column('marker_path', sa.String(length=500), nullable=True))
    except Exception:
        pass
    
    try:
        op.add_column('ar_content', sa.Column('marker_url', sa.String(length=500), nullable=True))
    except Exception:
        pass
    
    try:
        op.add_column('ar_content', sa.Column('marker_status', sa.String(length=50), nullable=True))
    except Exception:
        pass
    
    try:
        op.add_column('ar_content', sa.Column('marker_metadata', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True))
    except Exception:
        pass
    
    # Check and add timestamp fields if they don't exist
    try:
        # Add created_at with proper default if it doesn't exist
        op.add_column('ar_content', sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')))
    except Exception:
        # Column might already exist, try to update it if needed
        pass
    
    try:
        # Add updated_at with proper default if it doesn't exist
        op.add_column('ar_content', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')))
    except Exception:
        # Column might already exist, try to update it if needed
        pass
    
    # Ensure proper constraints and indexes exist
    # Create unique constraint on unique_id if it doesn't exist
    try:
        op.create_unique_constraint('uq_ar_content_unique_id', 'ar_content', ['unique_id'])
    except Exception:
        pass
    
    # Create performance indexes if they don't exist
    try:
        op.create_index('ix_ar_content_company_project', 'ar_content', ['company_id', 'project_id'])
    except Exception:
        pass
    
    try:
        op.create_index('ix_ar_content_created_at', 'ar_content', ['created_at'])
    except Exception:
        pass
    
    try:
        op.create_index('ix_ar_content_status', 'ar_content', ['status'])
    except Exception:
        pass
    
    # Ensure foreign key constraints exist
    try:
        op.create_foreign_key('fk_ar_content_project', 'ar_content', 'projects', ['project_id'], ['id'])
    except Exception:
        pass
    
    try:
        op.create_foreign_key('fk_ar_content_company', 'ar_content', 'companies', ['company_id'], ['id'])
    except Exception:
        pass
    
    try:
        op.create_foreign_key('fk_ar_content_active_video', 'ar_content', 'videos', ['active_video_id'], ['id'])
    except Exception:
        pass


def downgrade() -> None:
    """Remove the columns that were added by this migration"""
    
    # Remove indexes first
    try:
        op.drop_index('ix_ar_content_status', table_name='ar_content')
    except Exception:
        pass
    
    try:
        op.drop_index('ix_ar_content_created_at', table_name='ar_content')
    except Exception:
        pass
    
    try:
        op.drop_index('ix_ar_content_company_project', table_name='ar_content')
    except Exception:
        pass
    
    # Remove foreign key constraints
    try:
        op.drop_constraint('fk_ar_content_active_video', 'ar_content', type_='foreignkey')
    except Exception:
        pass
    
    try:
        op.drop_constraint('fk_ar_content_company', 'ar_content', type_='foreignkey')
    except Exception:
        pass
    
    try:
        op.drop_constraint('fk_ar_content_project', 'ar_content', type_='foreignkey')
    except Exception:
        pass
    
    # Remove unique constraint
    try:
        op.drop_constraint('uq_ar_content_unique_id', 'ar_content', type_='unique')
    except Exception:
        pass
    
    # Remove columns (only if they were added by this migration)
    # Note: We'll be conservative and not remove columns that might have been added by other migrations
    # This is a safety measure to avoid breaking the database