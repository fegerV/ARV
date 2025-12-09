"""Add storage companies relationship

Revision ID: 002_add_storage_companies_relationship
Revises: 001
Create Date: 2025-12-05 13:30:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_add_storage_companies_relationship'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add foreign key constraint to companies table
    op.create_foreign_key(
        'fk_companies_storage_connection_id',
        'companies',
        'storage_connections',
        ['storage_connection_id'],
        ['id']
    )


def downgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint('fk_companies_storage_connection_id', 'companies', type_='foreignkey')