"""Initial Vertex AR platform schema

Revision ID: 20251207_01_initial_vertex_ar
Revises: 
Create Date: 2025-12-07 16:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20251207_01_initial_vertex_ar"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Storage connections (нет внешних ключей)
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
        sa.Column("unique_id", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("image_path", sa.String(length=500), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("image_metadata", JSONB(), nullable=True),
        sa.Column("marker_path", sa.String(length=500), nullable=True),
        sa.Column("marker_url", sa.String(length=500), nullable=True),
        sa.Column("marker_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("marker_metadata", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("marker_generated_at", sa.DateTime(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
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
        sa.Column("video_path", sa.String(length=500), nullable=True),
        sa.Column("video_url", sa.String(length=500), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("thumbnail_small_url", sa.String(500), nullable=True),
        sa.Column("thumbnail_large_url", sa.String(500), nullable=True),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column("rotation_weight", sa.Integer(), nullable=False, server_default='1'),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_videos_id", "videos", ["id"])
    op.create_index("ix_videos_ar_content_id", "videos", ["ar_content_id"])

    # 6) Video rotation rules (FK → ar_content)
    op.create_table(
        "video_rotation_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ar_content_id", sa.Integer(), sa.ForeignKey("ar_content.id"), nullable=False, unique=True),
        sa.Column("rule_type", sa.String(length=50), nullable=False),  # daily_cycle/date_specific/random_daily
        sa.Column("daily_start_time", sa.Time(), nullable=True),
        sa.Column("daily_end_time", sa.Time(), nullable=True),
        sa.Column("specific_dates", JSONB(), nullable=True),  # array of dates
        sa.Column("timezone", sa.String(length=50), nullable=False, server_default="UTC"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_video_rotation_rules_id", "video_rotation_rules", ["id"])
    op.create_index("ix_video_rotation_rules_ar_content_id", "video_rotation_rules", ["ar_content_id"])

    # 7) Video rotation schedules (FK → ar_content, videos)
    op.create_table(
        "video_rotation_schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ar_content_id", sa.Integer(), sa.ForeignKey("ar_content.id"), nullable=False),
        sa.Column("video_id", sa.Integer(), sa.ForeignKey("videos.id"), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("scheduled_time", sa.Time(), nullable=False),
        sa.Column("next_rotation_at", sa.DateTime(), nullable=True),
        sa.Column("played_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),  # pending, played, skipped
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_video_rotation_schedules_id", "video_rotation_schedules", ["id"])
    op.create_index("ix_video_rotation_schedules_ar_content_id", "video_rotation_schedules", ["ar_content_id"])
    op.create_index("ix_video_rotation_schedules_scheduled_date", "video_rotation_schedules", ["scheduled_date"])

    # 8) AR view sessions (аналитика, FK → ar_content, company)
    op.create_table(
        "ar_view_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=128), nullable=False),  # UUID for session tracking
        sa.Column("ar_content_id", sa.Integer(), sa.ForeignKey("ar_content.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("device_info", JSONB(), nullable=True),
        sa.Column("browser_info", JSONB(), nullable=True),
        sa.Column("location", JSONB(), nullable=True),  # latitude, longitude, city, country
        sa.Column("ip_address", sa.String(length=45), nullable=True),  # IPv4 or IPv6
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("referer", sa.String(length=500), nullable=True),
        sa.Column("fps_samples", JSONB(), nullable=True),  # array of fps measurements
        sa.Column("average_fps", sa.Float(), nullable=True),
        sa.Column("session_duration", sa.Integer(), nullable=True),  # in seconds
        sa.Column("video_started_at", sa.DateTime(), nullable=True),
        sa.Column("video_ended_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ar_view_sessions_id", "ar_view_sessions", ["id"])
    op.create_index("ix_ar_view_sessions_ar_content_id", "ar_view_sessions", ["ar_content_id"])
    op.create_index("ix_ar_view_sessions_company_id", "ar_view_sessions", ["company_id"])
    op.create_index("ix_ar_view_sessions_session_id", "ar_view_sessions", ["session_id"])
    
    # 9) Notifications (FK → companies, users)
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("type", sa.String(length=50), nullable=False),  # expiry_warning, critical_alert, info
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="normal"),  # low, normal, high, urgent
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("related_entity_type", sa.String(length=50), nullable=True),  # ar_content, project, company
        sa.Column("related_entity_id", sa.Integer(), nullable=True),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_id", "notifications", ["id"])
    op.create_index("ix_notifications_company_id", "notifications", ["company_id"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])
    op.create_index("ix_notifications_priority", "notifications", ["priority"])
    
    # 10) Create performance indexes
    # Analytics: AR view sessions heavy queries
    op.create_index(
        'idx_ar_sessions_company_created',
        'ar_view_sessions',
        ['company_id', 'created_at'],
        unique=False,
    )
    op.create_index(
        'idx_ar_sessions_content',
        'ar_view_sessions',
        ['ar_content_id'],
        unique=False,
    )

    # Companies
    op.create_index(
        'idx_companies_slug_active',
        'companies',
        ['slug'],
        unique=False,
        postgresql_where=sa.text('is_active = true'),
    )

    # Projects
    op.create_index(
        'idx_projects_company_status',
        'projects',
        ['company_id', 'status'],
        unique=False,
    )

    # Video rotation schedules
    # Skipping index on next_rotation_at for now


def downgrade() -> None:
    # Удаляем в обратном порядке зависимостей
    # Drop indexes first
    op.drop_index('idx_rotation_schedules_next', table_name='video_rotation_schedules')
    op.drop_index('idx_projects_company_status', table_name='projects')
    op.drop_index('idx_companies_slug_active', table_name='companies')
    op.drop_index('idx_ar_sessions_content', table_name='ar_view_sessions')
    op.drop_index('idx_ar_sessions_company_created', table_name='ar_view_sessions')
    
    op.drop_index("ix_notifications_priority", table_name="notifications")
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_index("ix_notifications_company_id", table_name="notifications")
    op.drop_index("ix_notifications_id", table_name="notifications")
    op.drop_table("notifications")
    
    op.drop_index("ix_ar_view_sessions_session_id", table_name="ar_view_sessions")
    op.drop_index("ix_ar_view_sessions_company_id", table_name="ar_view_sessions")
    op.drop_index("ix_ar_view_sessions_ar_content_id", table_name="ar_view_sessions")
    op.drop_index("ix_ar_view_sessions_id", table_name="ar_view_sessions")
    op.drop_table("ar_view_sessions")

    op.drop_index("ix_video_rotation_schedules_scheduled_date", table_name="video_rotation_schedules")
    op.drop_index("ix_video_rotation_schedules_ar_content_id", table_name="video_rotation_schedules")
    op.drop_index("ix_video_rotation_schedules_id", table_name="video_rotation_schedules")
    op.drop_table("video_rotation_schedules")
    
    op.drop_index("ix_video_rotation_rules_ar_content_id", table_name="video_rotation_rules")
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