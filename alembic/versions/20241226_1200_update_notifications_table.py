"""update notifications table structure

Revision ID: update_notifications_2024
Revises: 28cd993514df
Create Date: 2024-12-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'update_notifications_2024'
down_revision: Union[str, None] = '20251223_1200_comprehensive_ar_content_fix'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update notifications table to match the model
    with op.batch_alter_table('notifications') as batch_op:
        # Add new columns
        batch_op.add_column(sa.Column('company_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('project_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('ar_content_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('notification_type', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('email_sent', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('email_sent_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('email_error', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('telegram_sent', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('telegram_sent_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('telegram_error', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('subject', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('metadata', sa.JSON(), nullable=True))
        
        # Drop old columns (optional - comment out if you want to keep them)
        # batch_op.drop_column('priority')
        # batch_op.drop_column('recipient_id')
        # batch_op.drop_column('sender_id')
        
        # Make title and message nullable to match the model
        batch_op.alter_column('title', nullable=True)
        batch_op.alter_column('message', nullable=True)
        batch_op.alter_column('type', nullable=True)
        batch_op.alter_column('is_read', nullable=True)


def downgrade() -> None:
    # Revert changes
    with op.batch_alter_table('notifications') as batch_op:
        # Drop new columns
        batch_op.drop_column('metadata')
        batch_op.drop_column('subject')
        batch_op.drop_column('telegram_error')
        batch_op.drop_column('telegram_sent_at')
        batch_op.drop_column('telegram_sent')
        batch_op.drop_column('email_error')
        batch_op.drop_column('email_sent_at')
        batch_op.drop_column('email_sent')
        batch_op.drop_column('notification_type')
        batch_op.drop_column('ar_content_id')
        batch_op.drop_column('project_id')
        batch_op.drop_column('company_id')
        
        # Restore old column constraints
        batch_op.alter_column('title', nullable=False)
        batch_op.alter_column('message', nullable=False)
        batch_op.alter_column('type', nullable=False)
        batch_op.alter_column('is_read', nullable=False)