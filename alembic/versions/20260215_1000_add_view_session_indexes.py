"""Add missing columns and indexes to ar_view_sessions.

Revision ID: 20260215_1000_idx
Revises: 20260214_1400_bkp
Create Date: 2026-02-15 10:00:00

The ar_view_sessions model was extended with analytics columns
(project_id, company_id, device_type, browser, os, country, city,
tracking_quality, video_played) but the table was never migrated.
This caused UndefinedColumnError on every AR view (500 errors).

Also adds performance indexes for analytics queries.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260215_1000_idx"
down_revision: Union[str, None] = "20260214_1400_bkp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Add missing columns ───────────────────────────────────────
    op.add_column(
        "ar_view_sessions",
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True),
    )
    op.add_column(
        "ar_view_sessions",
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
    )
    op.add_column(
        "ar_view_sessions",
        sa.Column("device_type", sa.String(50), nullable=True),
    )
    op.add_column(
        "ar_view_sessions",
        sa.Column("browser", sa.String(100), nullable=True),
    )
    op.add_column(
        "ar_view_sessions",
        sa.Column("os", sa.String(100), nullable=True),
    )
    op.add_column(
        "ar_view_sessions",
        sa.Column("country", sa.String(100), nullable=True),
    )
    op.add_column(
        "ar_view_sessions",
        sa.Column("city", sa.String(100), nullable=True),
    )
    op.add_column(
        "ar_view_sessions",
        sa.Column("tracking_quality", sa.String(50), nullable=True),
    )
    op.add_column(
        "ar_view_sessions",
        sa.Column("video_played", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )

    # Drop legacy 'location' column (replaced by country + city)
    op.drop_column("ar_view_sessions", "location")

    # ── 2. Performance indexes ───────────────────────────────────────
    op.create_index(
        "ix_ar_view_sessions_created_at",
        "ar_view_sessions",
        ["created_at"],
    )
    op.create_index(
        "ix_ar_view_sessions_company_id",
        "ar_view_sessions",
        ["company_id"],
    )
    op.create_index(
        "ix_ar_view_sessions_project_id",
        "ar_view_sessions",
        ["project_id"],
    )
    op.create_index(
        "ix_ar_view_sessions_ar_content_id",
        "ar_view_sessions",
        ["ar_content_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ar_view_sessions_ar_content_id", table_name="ar_view_sessions")
    op.drop_index("ix_ar_view_sessions_project_id", table_name="ar_view_sessions")
    op.drop_index("ix_ar_view_sessions_company_id", table_name="ar_view_sessions")
    op.drop_index("ix_ar_view_sessions_created_at", table_name="ar_view_sessions")

    op.add_column(
        "ar_view_sessions",
        sa.Column("location", sa.String(255), nullable=True),
    )

    op.drop_column("ar_view_sessions", "video_played")
    op.drop_column("ar_view_sessions", "tracking_quality")
    op.drop_column("ar_view_sessions", "city")
    op.drop_column("ar_view_sessions", "country")
    op.drop_column("ar_view_sessions", "os")
    op.drop_column("ar_view_sessions", "browser")
    op.drop_column("ar_view_sessions", "device_type")
    op.drop_column("ar_view_sessions", "company_id")
    op.drop_column("ar_view_sessions", "project_id")
