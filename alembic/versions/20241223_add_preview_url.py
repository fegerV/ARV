"""Add preview_url column to videos table

Revision ID: 20241223_add_preview_url
Revises: 20251223_schema_migration_overhaul
Create Date: 2024-12-23 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20241223_add_preview_url'
down_revision: Union[str, None] = '20251223_schema_migration_overhaul'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add preview_url column to videos table."""
    # Add preview_url column
    op.add_column('videos', sa.Column('preview_url', sa.String(length=500), nullable=True))
    
    # Add comment to the column
    op.execute("COMMENT ON COLUMN videos.preview_url IS 'Preview generated from middle frame'")


def downgrade() -> None:
    """Remove preview_url column from videos table."""
    op.drop_column('videos', 'preview_url')