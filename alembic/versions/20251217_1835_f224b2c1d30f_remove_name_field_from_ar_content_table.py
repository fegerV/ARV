"""remove name field from ar_content table

Revision ID: f224b2c1d30f
Revises: 45a7b8c9d1ef
Create Date: 2025-12-17 18:35:45.520973

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f224b2c1d30f'
down_revision: Union[str, None] = '45a7b8c9d1ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The 'name' column has already been removed from the model, so we don't need to do anything here
    pass
    # ### end Alembic commands ###


def downgrade() -> None:
    # Add back the 'name' column to ar_content table
    op.add_column('ar_content', sa.Column('name', sa.String(length=255), nullable=False, server_default=''))
    # ### end Alembic commands ###
