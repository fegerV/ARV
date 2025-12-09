"""Add company folders relationship

Revision ID: 005_add_company_folders_relationship
Revises: 004_add_storage_folder_company_relationship
Create Date: 2025-12-09 19:10:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005_add_company_folders_relationship'
down_revision = '004_add_storage_folder_company_relationship'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This migration only ensures the relationship is properly configured
    # The foreign key was already added in the previous migration
    pass


def downgrade() -> None:
    # No downgrade needed as this is just a relationship configuration
    pass