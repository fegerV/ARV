"""Create ai_jobs table for AI processing tasks.

Revision ID: 20260908_1200_create_ai_jobs_table
Revises: 20260824_1300_create_alerts_table
Create Date: 2026-09-08 12:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260908_1200_create_ai_jobs_table"
down_revision: Union[str, None] = "20260824_1300_create_alerts_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False, index=True),
        sa.Column("ar_content_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="queued"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("model_version", sa.String(length=100), nullable=False, server_default="default"),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["ar_content_id"], ["ar_content.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_ai_jobs_job_id", "ai_jobs", ["job_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_ai_jobs_job_id", table_name="ai_jobs")
    op.drop_table("ai_jobs")
