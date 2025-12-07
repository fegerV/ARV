"""Unified Vertex AR schema with correct foreign key dependency order:
storage_connections → companies → projects → ar_content → videos → video_rotation_rules → ar_view_sessions

Revision ID: 20251207_02_unified_vertex_ar_entities
Revises: 20251207_01_initial_vertex_ar
Create Date: 2025-12-07 17:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = "20251207_02_unified_vertex_ar_entities"
down_revision = "20251207_01_initial_vertex_ar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Ensure all indexes exist for optimal query performance."""
    # For storage_connections table
    try:
        op.create_index("ix_storage_connections_id", "storage_connections", ["id"])
    except Exception:
        pass  # Index might already exist
    
    # For companies table
    try:
        op.create_index("ix_companies_id", "companies", ["id"])
        op.create_index("ix_companies_slug", "companies", ["slug"], unique=True)
    except Exception:
        pass  # Indexes might already exist
    
    # For projects table
    try:
        op.create_index("ix_projects_id", "projects", ["id"])
        op.create_index("ix_projects_company_slug", "projects", ["company_id", "slug"], unique=True)
    except Exception:
        pass  # Indexes might already exist
    
    # For ar_content table
    try:
        op.create_index("ix_ar_content_id", "ar_content", ["id"])
        op.create_index("ix_ar_content_unique_id", "ar_content", ["unique_id"], unique=True)
        op.create_index("ix_ar_content_company_id", "ar_content", ["company_id"])
        op.create_index("ix_ar_content_project_id", "ar_content", ["project_id"])
    except Exception:
        pass  # Indexes might already exist
    
    # For videos table
    try:
        op.create_index("ix_videos_id", "videos", ["id"])
        op.create_index("ix_videos_ar_content_id", "videos", ["ar_content_id"])
    except Exception:
        pass  # Indexes might already exist
    
    # For video_rotation_rules table
    try:
        op.create_index("ix_video_rotation_rules_id", "video_rotation_rules", ["id"])
    except Exception:
        pass  # Index might already exist
    
    # For ar_view_sessions table
    try:
        op.create_index("ix_ar_view_sessions_id", "ar_view_sessions", ["id"])
        op.create_index(
            "ix_ar_view_sessions_content_created",
            "ar_view_sessions",
            ["ar_content_id", "created_at"],
        )
    except Exception:
        pass  # Indexes might already exist


def downgrade() -> None:
    """Remove indexes for rollback."""
    # Drop indexes in reverse order
    try:
        op.drop_index("ix_ar_view_sessions_content_created", table_name="ar_view_sessions")
    except Exception:
        pass
        
    try:
        op.drop_index("ix_ar_view_sessions_id", table_name="ar_view_sessions")
    except Exception:
        pass
        
    try:
        op.drop_index("ix_video_rotation_rules_id", table_name="video_rotation_rules")
    except Exception:
        pass
        
    try:
        op.drop_index("ix_videos_ar_content_id", table_name="videos")
    except Exception:
        pass
        
    try:
        op.drop_index("ix_videos_id", table_name="videos")
    except Exception:
        pass
        
    try:
        op.drop_index("ix_ar_content_project_id", table_name="ar_content")
    except Exception:
        pass
        
    try:
        op.drop_index("ix_ar_content_company_id", table_name="ar_content")
    except Exception:
        pass
        
    try:
        op.drop_index("ix_ar_content_unique_id", table_name="ar_content")
    except Exception:
        pass
        
    try:
        op.drop_index("ix_ar_content_id", table_name="ar_content")
    except Exception:
        pass
        
    try:
        op.drop_index("ix_projects_company_slug", table_name="projects")
    except Exception:
        pass
        
    try:
        op.drop_index("ix_projects_id", table_name="projects")
    except Exception:
        pass
        
    try:
        op.drop_index("ix_companies_slug", table_name="companies")
    except Exception:
        pass
        
    try:
        op.drop_index("ix_companies_id", table_name="companies")
    except Exception:
        pass
        
    try:
        op.drop_index("ix_storage_connections_id", table_name="storage_connections")
    except Exception:
        pass