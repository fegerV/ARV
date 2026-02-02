"""add rotation_weight and is_default to videos table

Revision ID: 20260127_1310_add_video_fields
Revises: 20260127_1300_extend_rotation
Create Date: 2025-01-27 13:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260127_1310_add_video_fields'
down_revision: Union[str, None] = '20260127_1300_extend_rotation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add rotation_weight and is_default columns to videos table"""
    try:
        op.add_column('videos',
            sa.Column('rotation_weight', sa.Integer(), nullable=True, server_default='1'))
    except Exception:
        pass
    
    try:
        op.add_column('videos',
            sa.Column('is_default', sa.Boolean(), nullable=True, server_default='false'))
    except Exception:
        pass


def downgrade() -> None:
    """Remove rotation_weight and is_default columns from videos table"""
    try:
        op.drop_column('videos', 'rotation_weight')
    except Exception:
        pass
    
    try:
        op.drop_column('videos', 'is_default')
    except Exception:
        pass
