"""Add performance indexes for analytics, companies, projects, and rotation schedules

Revision ID: 20251205_perf_idx
Revises: 
Create Date: 2025-12-05
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251205_perf_idx'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
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
    op.create_index(
        'idx_rotation_schedules_next',
        'video_rotation_schedules',
        ['next_rotation_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('idx_rotation_schedules_next', table_name='video_rotation_schedules')
    op.drop_index('idx_projects_company_status', table_name='projects')
    op.drop_index('idx_companies_slug_active', table_name='companies')
    op.drop_index('idx_ar_sessions_content', table_name='ar_view_sessions')
    op.drop_index('idx_ar_sessions_company_created', table_name='ar_view_sessions')
