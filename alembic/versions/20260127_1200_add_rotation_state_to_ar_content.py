"""add rotation_state to ar_content table

Revision ID: 20260127_1200_add_rotation_state
Revises: 20260127_remove_notifications_priority
Create Date: 2025-01-27 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260127_1200_add_rotation_state'
down_revision: Union[str, None] = 'remove_notifications_priority'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add rotation_state column to ar_content table"""
    try:
        op.add_column('ar_content', 
            sa.Column('rotation_state', sa.Integer(), nullable=True, server_default='0'))
    except Exception:
        # Column might already exist, which is fine
        pass


def downgrade() -> None:
    """Remove rotation_state column from ar_content table"""
    try:
        op.drop_column('ar_content', 'rotation_state')
    except Exception:
        # Column might not exist, which is fine
        pass
