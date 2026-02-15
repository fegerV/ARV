"""Add performance indexes to ar_view_sessions.

Revision ID: 20260215_1000_idx
Revises: 20260214_1400_bkp
Create Date: 2026-02-15 10:00:00

The ar_view_sessions table grows with every AR scan. Analytics queries
filter by created_at, company_id, project_id, and ar_content_id but
had no indexes, causing sequential scans on large tables.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "20260215_1000_idx"
down_revision: Union[str, None] = "20260214_1400_bkp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
