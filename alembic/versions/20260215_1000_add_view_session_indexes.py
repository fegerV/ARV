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


def _column_names(conn, table_name: str) -> set[str]:
    inspector = sa.inspect(conn)
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(conn, table_name: str) -> set[str]:
    inspector = sa.inspect(conn)
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    conn = op.get_bind()
    existing_columns = _column_names(conn, "ar_view_sessions")
    existing_indexes = _index_names(conn, "ar_view_sessions")

    project_col = (
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True)
        if conn.dialect.name == "postgresql"
        else sa.Column("project_id", sa.Integer(), nullable=True)
    )
    company_col = (
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True)
        if conn.dialect.name == "postgresql"
        else sa.Column("company_id", sa.Integer(), nullable=True)
    )

    columns_to_add = [
        ("project_id", project_col),
        ("company_id", company_col),
        ("device_type", sa.Column("device_type", sa.String(50), nullable=True)),
        ("browser", sa.Column("browser", sa.String(100), nullable=True)),
        ("os", sa.Column("os", sa.String(100), nullable=True)),
        ("country", sa.Column("country", sa.String(100), nullable=True)),
        ("city", sa.Column("city", sa.String(100), nullable=True)),
        ("tracking_quality", sa.Column("tracking_quality", sa.String(50), nullable=True)),
        (
            "video_played",
            sa.Column("video_played", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        ),
    ]
    for column_name, column in columns_to_add:
        if column_name not in existing_columns:
            op.add_column("ar_view_sessions", column)

    if "location" in existing_columns:
        op.drop_column("ar_view_sessions", "location")

    index_specs = [
        ("ix_ar_view_sessions_created_at", ["created_at"]),
        ("ix_ar_view_sessions_company_id", ["company_id"]),
        ("ix_ar_view_sessions_project_id", ["project_id"]),
        ("ix_ar_view_sessions_ar_content_id", ["ar_content_id"]),
    ]
    for index_name, columns in index_specs:
        if index_name not in existing_indexes:
            op.create_index(index_name, "ar_view_sessions", columns)


def downgrade() -> None:
    conn = op.get_bind()
    existing_columns = _column_names(conn, "ar_view_sessions")
    existing_indexes = _index_names(conn, "ar_view_sessions")

    for index_name in [
        "ix_ar_view_sessions_ar_content_id",
        "ix_ar_view_sessions_project_id",
        "ix_ar_view_sessions_company_id",
        "ix_ar_view_sessions_created_at",
    ]:
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name="ar_view_sessions")

    if "location" not in existing_columns:
        op.add_column(
            "ar_view_sessions",
            sa.Column("location", sa.String(255), nullable=True),
        )

    for column_name in [
        "video_played",
        "tracking_quality",
        "city",
        "country",
        "os",
        "browser",
        "device_type",
        "company_id",
        "project_id",
    ]:
        if column_name in existing_columns:
            op.drop_column("ar_view_sessions", column_name)
