#!/usr/bin/env python3
"""
Exact Vertex AR schema creation code as specified.

This file contains the exact table creation code in the correct dependency order:
storage_connections → companies → projects → ar_content → videos → video_rotation_rules → ar_view_sessions
"""

# Exact schema creation code as specified
def get_exact_schema_creation_code():
    """Returns the exact schema creation code as specified."""
    schema_code = '''
"""Alembic migration script for unified Vertex AR schema."""

from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    """Create all Vertex AR entities in the correct foreign key dependency order."""
    
    # 1) Storage connections (no foreign keys)
    op.create_table(
        "storage_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), unique=True, nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("base_path", sa.String(length=500), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("test_status", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_storage_connections_id", "storage_connections", ["id"])

    # 2) Companies (FK → storage_connections)
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False, unique=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column(
            "storage_connection_id",
            sa.Integer(),
            sa.ForeignKey("storage_connections.id"),
            nullable=False,
        ),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("storage_quota_gb", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("storage_used_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_companies_id", "companies", ["id"])
    op.create_index("ix_companies_slug", "companies", ["slug"], unique=True)

    # 3) Projects (FK → companies)
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("folder_path", sa.String(length=500), nullable=False),
        sa.Column("project_type", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_projects_id", "projects", ["id"])
    op.create_index("ix_projects_company_slug", "projects", ["company_id", "slug"], unique=True)

    # 4) ARContent (FK → projects, companies)
    op.create_table(
        "ar_content",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("unique_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("image_path", sa.String(length=500), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("image_metadata", sa.JSON(), nullable=True),
        sa.Column("marker_path", sa.String(length=500), nullable=True),
        sa.Column("marker_url", sa.String(length=500), nullable=True),
        sa.Column("marker_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("marker_metadata", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ar_content_id", "ar_content", ["id"])
    op.create_index("ix_ar_content_unique_id", "ar_content", ["unique_id"], unique=True)
    op.create_index("ix_ar_content_company_id", "ar_content", ["company_id"])
    op.create_index("ix_ar_content_project_id", "ar_content", ["project_id"])

    # 5) Videos (FK → ar_content)
    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ar_content_id", sa.Integer(), sa.ForeignKey("ar_content.id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("video_path", sa.String(length=500), nullable=False),
        sa.Column("video_url", sa.String(length=500), nullable=False),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_videos_id", "videos", ["id"])
    op.create_index("ix_videos_ar_content_id", "videos", ["ar_content_id"])

    # 6) Video rotation rules (FK → ar_content, videos)
    op.create_table(
        "video_rotation_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ar_content_id", sa.Integer(), sa.ForeignKey("ar_content.id"), nullable=False, unique=True),
        sa.Column("rotation_type", sa.String(length=50), nullable=False),  # fixed/daily/date_specific/random_daily
        sa.Column("default_video_id", sa.Integer(), sa.ForeignKey("videos.id"), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("next_change_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_video_rotation_rules_id", "video_rotation_rules", ["id"])

    # 7) AR view sessions (analytics, FK → ar_content, company)
    op.create_table(
        "ar_view_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("ar_content_id", sa.Integer(), sa.ForeignKey("ar_content.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("device_type", sa.String(length=32), nullable=True),  # mobile/tablet/desktop
        sa.Column("os", sa.String(length=50), nullable=True),
        sa.Column("os_version", sa.String(length=50), nullable=True),
        sa.Column("browser", sa.String(length=50), nullable=True),
        sa.Column("browser_version", sa.String(length=50), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("marker_detected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("video_played", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("avg_fps", sa.Float(), nullable=True),
        sa.Column("tracking_quality", sa.String(length=50), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ar_view_sessions_id", "ar_view_sessions", ["id"])
    op.create_index(
        "ix_ar_view_sessions_content_created",
        "ar_view_sessions",
        ["ar_content_id", "created_at"],
    )


def downgrade() -> None:
    """Drop all Vertex AR entities in reverse dependency order."""
    # Drop in reverse order of dependencies
    op.drop_index("ix_ar_view_sessions_content_created", table_name="ar_view_sessions")
    op.drop_index("ix_ar_view_sessions_id", table_name="ar_view_sessions")
    op.drop_table("ar_view_sessions")

    op.drop_index("ix_video_rotation_rules_id", table_name="video_rotation_rules")
    op.drop_table("video_rotation_rules")

    op.drop_index("ix_videos_ar_content_id", table_name="videos")
    op.drop_index("ix_videos_id", table_name="videos")
    op.drop_table("videos")

    op.drop_index("ix_ar_content_project_id", table_name="ar_content")
    op.drop_index("ix_ar_content_company_id", table_name="ar_content")
    op.drop_index("ix_ar_content_unique_id", table_name="ar_content")
    op.drop_index("ix_ar_content_id", table_name="ar_content")
    op.drop_table("ar_content")

    op.drop_index("ix_projects_company_slug", table_name="projects")
    op.drop_index("ix_projects_id", table_name="projects")
    op.drop_table("projects")

    op.drop_index("ix_companies_slug", table_name="companies")
    op.drop_index("ix_companies_id", table_name="companies")
    op.drop_table("companies")

    op.drop_index("ix_storage_connections_id", table_name="storage_connections")
    op.drop_table("storage_connections")
'''
    return schema_code


if __name__ == "__main__":
    print("Vertex AR Schema - Exact Specification")
    print("=" * 50)
    print("Entity creation order:")
    print("1. storage_connections (no foreign keys)")
    print("2. companies (FK → storage_connections)")
    print("3. projects (FK → companies)")
    print("4. ar_content (FK → projects, companies)")
    print("5. videos (FK → ar_content)")
    print("6. video_rotation_rules (FK → ar_content, videos)")
    print("7. ar_view_sessions (FK → ar_content, companies)")
    print("\n" + "=" * 50)
    print("Schema creation code:")
    print(get_exact_schema_creation_code())