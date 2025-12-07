"""Add missing fields for videos, ar_content, storage_folders

Revision ID: 20251205_add_missing_fields
Revises: 0015_create_demo_data
Create Date: 2025-12-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '20251205_add_missing_fields'
down_revision = '0015_create_demo_data'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # videos: rotation_weight, is_default
    op.add_column(
        'videos',
        sa.Column('rotation_weight', sa.Integer(), nullable=False, server_default='1'),
    )
    op.add_column(
        'videos',
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )
    # remove server defaults (keep application-level defaults)
    op.alter_column('videos', 'rotation_weight', server_default=None)
    op.alter_column('videos', 'is_default', server_default=None)

    # ar_content: marker_metadata JSONB
    op.add_column(
        'ar_content',
        sa.Column('marker_metadata', JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    # optional: keep default for future inserts; do not remove server_default

    # storage_folders: full_path (unique, backfill from path)
    op.add_column(
        'storage_folders',
        sa.Column('full_path', sa.String(length=500), nullable=True),
    )
    # backfill from existing 'path' column if present
    op.execute("UPDATE storage_folders SET full_path = path WHERE full_path IS NULL")
    # enforce NOT NULL and unique index
    op.alter_column('storage_folders', 'full_path', nullable=False)
    op.create_index('ux_storage_folders_full_path', 'storage_folders', ['full_path'], unique=True)


def downgrade() -> None:
    # storage_folders: drop index and column
    op.drop_index('ux_storage_folders_full_path', table_name='storage_folders')
    op.drop_column('storage_folders', 'full_path')

    # ar_content: drop marker_metadata
    op.drop_column('ar_content', 'marker_metadata')

    # videos: drop added columns
    op.drop_column('videos', 'is_default')
    op.drop_column('videos', 'rotation_weight')