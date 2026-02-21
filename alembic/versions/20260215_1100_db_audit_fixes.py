"""Database audit fixes: indexes, FK constraints, NOT NULL, column types.

Revision ID: 20260215_1100_dbaudit
Revises: 20260215_1000_idx
Create Date: 2026-02-15 11:00:00

Comprehensive migration addressing the database audit findings:
- Add missing indexes on FK columns (skips if already exists)
- Add FK constraints to notifications table
- Add unique index on companies.slug
- Add updated_at to notifications
- Change clients.is_active from String to Boolean
- Change folders.is_active from String to Boolean
- Change video.size_bytes from Integer to BigInteger
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260215_1100_dbaudit"
down_revision: Union[str, None] = "20260215_1000_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_index_if_not_exists(name: str, table: str, columns: list[str], **kw: object) -> None:
    """Create index only if it does not already exist (PostgreSQL)."""
    unique = "UNIQUE " if kw.get("unique") else ""
    cols = ", ".join(columns)
    op.execute(
        sa.text(f"CREATE {unique}INDEX IF NOT EXISTS {name} ON {table} ({cols})")
    )


def upgrade() -> None:
    # ── FK indexes (skip if already exists) ───────────────────────────
    _create_index_if_not_exists("ix_videos_ar_content_id", "videos", ["ar_content_id"])
    _create_index_if_not_exists("ix_clients_company_id", "clients", ["company_id"])
    _create_index_if_not_exists("ix_folders_project_id", "folders", ["project_id"])
    _create_index_if_not_exists("ix_folders_parent_id", "folders", ["parent_id"])
    _create_index_if_not_exists("ix_video_schedules_video_id", "video_schedules", ["video_id"])
    _create_index_if_not_exists("ix_vrs_ar_content_id", "video_rotation_schedules", ["ar_content_id"])
    _create_index_if_not_exists("ix_storage_folders_company_id", "storage_folders", ["company_id"])
    _create_index_if_not_exists("ix_backup_history_company_id", "backup_history", ["company_id"])
    _create_index_if_not_exists("ix_backup_history_started_at", "backup_history", ["started_at"])
    _create_index_if_not_exists("ix_ar_content_active_video_id", "ar_content", ["active_video_id"])

    # ── Unique index on companies.slug ────────────────────────────────
    _create_index_if_not_exists("ix_companies_slug", "companies", ["slug"], unique=True)

    # ── Notifications: add FK constraints + indexes + updated_at ──────
    op.add_column("notifications", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.execute(sa.text("UPDATE notifications SET updated_at = created_at WHERE updated_at IS NULL"))

    _create_index_if_not_exists("ix_notifications_company_id", "notifications", ["company_id"])
    _create_index_if_not_exists("ix_notifications_created_at", "notifications", ["created_at"])
    _create_index_if_not_exists("ix_notifications_type", "notifications", ["notification_type"])

    # Clean up orphaned references before adding FK constraints
    op.execute(sa.text(
        "UPDATE notifications SET company_id = NULL "
        "WHERE company_id IS NOT NULL "
        "AND company_id NOT IN (SELECT id FROM companies)"
    ))
    op.execute(sa.text(
        "UPDATE notifications SET project_id = NULL "
        "WHERE project_id IS NOT NULL "
        "AND project_id NOT IN (SELECT id FROM projects)"
    ))
    op.execute(sa.text(
        "UPDATE notifications SET ar_content_id = NULL "
        "WHERE ar_content_id IS NOT NULL "
        "AND ar_content_id NOT IN (SELECT id FROM ar_content)"
    ))

    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.create_foreign_key(
            "fk_notifications_company_id_companies",
            "notifications", "companies",
            ["company_id"], ["id"],
        )
        op.create_foreign_key(
            "fk_notifications_project_id_projects",
            "notifications", "projects",
            ["project_id"], ["id"],
        )
        op.create_foreign_key(
            "fk_notifications_ar_content_id_ar_content",
            "notifications", "ar_content",
            ["ar_content_id"], ["id"],
        )

    # ── Email queue indexes ───────────────────────────────────────────
    _create_index_if_not_exists("ix_email_queue_status", "email_queue", ["status"])
    _create_index_if_not_exists("ix_email_queue_scheduled_at", "email_queue", ["scheduled_at"])
    _create_index_if_not_exists("ix_email_queue_created_at", "email_queue", ["created_at"])

    # ── System settings index (skip if already exists) ────────────────
    _create_index_if_not_exists("ix_system_settings_category", "system_settings", ["category"])

    # ── Column type changes (PostgreSQL only; SQLite Integer≈BigInteger) ─
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.alter_column(
            "videos", "size_bytes",
            type_=sa.BigInteger(),
            existing_type=sa.Integer(),
            existing_nullable=True,
        )

    # clients.is_active: String -> Boolean (data migration)
    op.add_column("clients", sa.Column("is_active_new", sa.Boolean(), server_default="true", nullable=False))
    op.execute(sa.text("UPDATE clients SET is_active_new = CASE WHEN is_active = 'active' THEN true ELSE false END"))
    op.drop_column("clients", "is_active")
    op.alter_column("clients", "is_active_new", new_column_name="is_active")

    # folders.is_active: String -> Boolean (data migration)
    op.add_column("folders", sa.Column("is_active_new", sa.Boolean(), server_default="true", nullable=False))
    op.execute(sa.text("UPDATE folders SET is_active_new = CASE WHEN is_active = 'active' THEN true ELSE false END"))
    op.drop_column("folders", "is_active")
    op.alter_column("folders", "is_active_new", new_column_name="is_active")


def downgrade() -> None:
    conn = op.get_bind()
    # ── Reverse column type changes ───────────────────────────────────
    op.add_column("folders", sa.Column("is_active_old", sa.String(50), server_default="active"))
    op.execute(sa.text("UPDATE folders SET is_active_old = CASE WHEN is_active THEN 'active' ELSE 'inactive' END"))
    op.drop_column("folders", "is_active")
    op.alter_column("folders", "is_active_old", new_column_name="is_active")

    op.add_column("clients", sa.Column("is_active_old", sa.String(50), server_default="active"))
    op.execute(sa.text("UPDATE clients SET is_active_old = CASE WHEN is_active THEN 'active' ELSE 'inactive' END"))
    op.drop_column("clients", "is_active")
    op.alter_column("clients", "is_active_old", new_column_name="is_active")

    if conn.dialect.name == "postgresql":
        op.alter_column(
            "videos", "size_bytes",
            type_=sa.Integer(),
            existing_type=sa.BigInteger(),
            existing_nullable=True,
        )

    # ── Drop new indexes (only those we know we created) ──────────────
    op.drop_index("ix_email_queue_created_at", table_name="email_queue")
    op.drop_index("ix_email_queue_scheduled_at", table_name="email_queue")
    op.drop_index("ix_email_queue_status", table_name="email_queue")

    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.drop_constraint("fk_notifications_ar_content_id_ar_content", "notifications", type_="foreignkey")
        op.drop_constraint("fk_notifications_project_id_projects", "notifications", type_="foreignkey")
        op.drop_constraint("fk_notifications_company_id_companies", "notifications", type_="foreignkey")

    op.drop_index("ix_notifications_type", table_name="notifications")
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_company_id", table_name="notifications")
    op.drop_column("notifications", "updated_at")

    op.drop_index("ix_companies_slug", table_name="companies")
    op.drop_index("ix_ar_content_active_video_id", table_name="ar_content")
    op.drop_index("ix_backup_history_started_at", table_name="backup_history")
    op.drop_index("ix_backup_history_company_id", table_name="backup_history")
    op.drop_index("ix_storage_folders_company_id", table_name="storage_folders")
    op.drop_index("ix_vrs_ar_content_id", table_name="video_rotation_schedules")
    op.drop_index("ix_folders_parent_id", table_name="folders")
    op.drop_index("ix_folders_project_id", table_name="folders")
    op.drop_index("ix_clients_company_id", table_name="clients")
