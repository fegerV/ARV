"""create ar_content table

Revision ID: 20251206_01_create_ar_content
Revises: 20251205_thumbnails
Create Date: 2025-12-06 12:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision = '20251206_01_create_ar_content'
down_revision = '003_create_users'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ar_content",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),

        sa.Column("unique_id", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),

        sa.Column("image_path", sa.String(length=500), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("image_metadata", JSONB(), nullable=True),

        sa.Column("marker_path", sa.String(length=500), nullable=True),
        sa.Column("marker_url", sa.String(length=500), nullable=True),
        sa.Column("marker_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("marker_metadata", JSONB(), nullable=True),

        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )

    op.create_index("ix_ar_content_id", "ar_content", ["id"])
    op.create_index("ix_ar_content_unique_id", "ar_content", ["unique_id"], unique=True)
    op.create_index("ix_ar_content_company_id", "ar_content", ["company_id"])
    op.create_index("ix_ar_content_project_id", "ar_content", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_ar_content_project_id", table_name="ar_content")
    op.drop_index("ix_ar_content_company_id", table_name="ar_content")
    op.drop_index("ix_ar_content_unique_id", table_name="ar_content")
    op.drop_index("ix_ar_content_id", table_name="ar_content")
    op.drop_table("ar_content")