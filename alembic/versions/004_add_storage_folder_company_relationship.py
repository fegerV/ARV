"""Add storage folder company relationship

Revision ID: 004_add_storage_folder_company_relationship
Revises: 003_create_users
Create Date: 2025-12-09 19:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_add_storage_folder_company_relationship'
down_revision = '003_create_users'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add foreign key constraint to storage_folders table
    op.create_foreign_key(
        'fk_storage_folders_company_id',
        'storage_folders',
        'companies',
        ['company_id'],
        ['id']
    )


def downgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint('fk_storage_folders_company_id', 'storage_folders', type_='foreignkey')