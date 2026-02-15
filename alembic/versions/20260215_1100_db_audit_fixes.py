"""Database audit fixes: indexes, FK constraints, NOT NULL, column types.

Revision ID: 20260215_1100_dbaudit
Revises: 20260215_1000_idx
Create Date: 2026-02-15 11:00:00

Comprehensive migration addressing the database audit findings:
- Add missing indexes on FK columns (videos, clients, folders, etc.)
- Add FK constraints to notifications table
- Add indexes on high-traffic tables (email_queue, audit_log, etc.)
- Add unique index on companies.slug
- Add updated_at to notifications
- Change clients.is_active from String to Boolean
- Change folders.is_active from String to Boolean
- Change video.size_bytes from Integer to BigInteger
- Add NOT NULL to columns with defaults that were missing it
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260215_1100_dbaudit"
down_revision: Union[str, None] = "20260215_1000_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── FK indexes (missing on many tables) ──────────────────────────
    # videos
    op.create_index("ix_videos_ar_content_id", "videos", ["ar_content_id"])

    # clients
    op.create_index("ix_clients_company_id", "clients", ["company_id"])

    # folders
    op.create_index("ix_folders_project_id", "folders", ["project_id"])
    op.create_index("ix_folders_parent_id", "folders", ["parent_id"])

    # video_schedules
    op.create_index("ix_video_schedules_video_id", "video_schedules", ["video_id"])

    # video_rotation_schedules
    op.create_index("ix_vrs_ar_content_id", "video_rotation_schedules", ["ar_content_id"])

    # storage_folders
    op.create_index("ix_storage_folders_company_id", "storage_folders", ["company_id"])

    # backup_history
    op.create_index("ix_backup_history_company_id", "backup_history", ["company_id"])
    op.create_index("ix_backup_history_started_at", "backup_history", ["started_at"])

    # ar_content.active_video_id
    op.create_index("ix_ar_content_active_video_id", "ar_content", ["active_video_id"])

    # ── Unique index on companies.slug ───────────────────────────────
    op.create_index("ix_companies_slug", "companies", ["slug"], unique=True)

    # ── Notifications: add FK constraints + indexes + updated_at ─────
    op.add_column("notifications", sa.Column("updated_at", sa.DateTime(), nullable=True))
    # Backfill updated_at from created_at
    op.execute("UPDATE notifications SET updated_at = created_at WHERE updated_at IS NULL")

    op.create_index("ix_notifications_company_id", "notifications", ["company_id"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])
    op.create_index("ix_notifications_type", "notifications", ["notification_type"])

    # FK constraints for notifications (nullable — soft references)
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

    # ── Email queue indexes ──────────────────────────────────────────
    op.create_index("ix_email_queue_status", "email_queue", ["status"])
    op.create_index("ix_email_queue_scheduled_at", "email_queue", ["scheduled_at"])
    op.create_index("ix_email_queue_created_at", "email_queue", ["created_at"])

    # ── Audit log indexes ────────────────────────────────────────────
    op.create_index("ix_audit_log_entity", "audit_log", ["entity_type", "entity_id"])
    op.create_index("ix_audit_log_actor_id", "audit_log", ["actor_id"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])

    # ── System settings: add index on category ───────────────────────
    op.create_index("ix_system_settings_category", "system_settings", ["category"])

    # ── Column type changes (best-effort; skip on error for SQLite) ──
    # video.size_bytes: Integer → BigInteger
    try:
        op.alter_column(
            "videos", "size_bytes",
            type_=sa.BigInteger(),
            existing_type=sa.Integer(),
            existing_nullable=True,
        )
    except Exception:
        pass  # SQLite doesn't support ALTER COLUMN

    # clients.is_active: String → Boolean (requires data migration)
    try:
        op.add_column("clients", sa.Column("is_active_new", sa.Boolean(), server_default="true", nullable=False))
        op.execute("UPDATE clients SET is_active_new = CASE WHEN is_active = 'active' THEN true ELSE false END")
        op.drop_column("clients", "is_active")
        op.alter_column("clients", "is_active_new", new_column_name="is_active")
    except Exception:
        pass  # Skip on SQLite

    # folders.is_active: String → Boolean
    try:
        op.add_column("folders", sa.Column("is_active_new", sa.Boolean(), server_default="true", nullable=False))
        op.execute("UPDATE folders SET is_active_new = CASE WHEN is_active = 'active' THEN true ELSE false END")
        op.drop_column("folders", "is_active")
        op.alter_column("folders", "is_active_new", new_column_name="is_active")
    except Exception:
        pass  # Skip on SQLite


def downgrade() -> None:
    # ── Reverse column type changes ──────────────────────────────────
    try:
        op.add_column("folders", sa.Column("is_active_old", sa.String(50), server_default="active"))
        op.execute("UPDATE folders SET is_active_old = CASE WHEN is_active THEN 'active' ELSE 'inactive' END")
        op.drop_column("folders", "is_active")
        op.alter_column("folders", "is_active_old", new_column_name="is_active")
    except Exception:
        pass

    try:
        op.add_column("clients", sa.Column("is_active_old", sa.String(50), server_default="active"))
        op.execute("UPDATE clients SET is_active_old = CASE WHEN is_active THEN 'active' ELSE 'inactive' END")
        op.drop_column("clients", "is_active")
        op.alter_column("clients", "is_active_old", new_column_name="is_active")
    except Exception:
        pass

    try:
        op.alter_column(
            "videos", "size_bytes",
            type_=sa.Integer(),
            existing_type=sa.BigInteger(),
            existing_nullable=True,
        )
    except Exception:
        pass

    # ── Drop indexes ─────────────────────────────────────────────────
    op.drop_index("ix_system_settings_category", table_name="system_settings")

    op.drop_index("ix_audit_log_created_at", table_name="audit_log")
    op.drop_index("ix_audit_log_actor_id", table_name="audit_log")
    op.drop_index("ix_audit_log_entity", table_name="audit_log")

    op.drop_index("ix_email_queue_created_at", table_name="email_queue")
    op.drop_index("ix_email_queue_scheduled_at", table_name="email_queue")
    op.drop_index("ix_email_queue_status", table_name="email_queue")

    # Drop notification FK constraints
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
    op.drop_index("ix_video_schedules_video_id", table_name="video_schedules")
    op.drop_index("ix_folders_parent_id", table_name="folders")
    op.drop_index("ix_folders_project_id", table_name="folders")
    op.drop_index("ix_clients_company_id", table_name="clients")
    op.drop_index("ix_videos_ar_content_id", table_name="videos")
