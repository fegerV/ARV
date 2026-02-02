"""remove priority column from notifications

Revision ID: remove_notifications_priority
Revises: update_notifications_2024
Create Date: 2026-01-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'remove_notifications_priority'
down_revision: Union[str, None] = '20260125_1204_add_missing_columns_to_clients'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove priority column and other old columns from notifications table."""
    # Check which columns exist before dropping
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('notifications')]
    
    columns_to_drop = ['priority', 'recipient_id', 'sender_id', 'title', 'type', 'is_read', 'updated_at']
    
    # Only drop columns that actually exist
    existing_columns_to_drop = [col for col in columns_to_drop if col in columns]
    
    if existing_columns_to_drop:
        with op.batch_alter_table('notifications') as batch_op:
            for col in existing_columns_to_drop:
                try:
                    batch_op.drop_column(col)
                except Exception:
                    pass  # Column might not exist


def downgrade() -> None:
    """Restore old columns (if needed for rollback)."""
    with op.batch_alter_table('notifications') as batch_op:
        # Add back old columns with defaults
        try:
            batch_op.add_column(sa.Column('priority', sa.String(length=20), nullable=True, server_default='normal'))
        except Exception:
            pass
        
        try:
            batch_op.add_column(sa.Column('recipient_id', sa.Integer(), nullable=True))
        except Exception:
            pass
        
        try:
            batch_op.add_column(sa.Column('sender_id', sa.Integer(), nullable=True))
        except Exception:
            pass
        
        try:
            batch_op.add_column(sa.Column('title', sa.String(length=255), nullable=True))
        except Exception:
            pass
        
        try:
            batch_op.add_column(sa.Column('type', sa.String(length=50), nullable=True))
        except Exception:
            pass
        
        try:
            batch_op.add_column(sa.Column('is_read', sa.Boolean(), nullable=True, server_default='0'))
        except Exception:
            pass
        
        try:
            batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))
        except Exception:
            pass
