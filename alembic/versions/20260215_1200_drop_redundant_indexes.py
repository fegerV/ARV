"""Drop redundant indexes to reduce write overhead and disk/RAM usage.

Revision ID: 20260215_1200_dedup
Revises: 20260215_1100_dbaudit
Create Date: 2026-02-15 12:00:00

Removes 8 duplicate indexes:
- ix_ar_content_id        : duplicate of ar_content_pkey
- uq_ar_content_unique_id : duplicate of ar_content_unique_id_key (UNIQUE constraint)
- ix_ar_content_company_id: covered by composite ix_ar_content_company_project
- ix_ar_content_project_id: covered by composite ix_ar_content_project_order
- ix_users_id             : duplicate of users_pkey
- ix_videos_id            : duplicate of videos_pkey
- ix_projects_id          : duplicate of projects_pkey
- ix_companies_id         : duplicate of companies_pkey

Each INSERT/UPDATE no longer maintains 8 extra B-tree structures.
At 100K ar_content rows this frees ~40 MB of RAM/disk.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260215_1200_dedup"
down_revision: Union[str, None] = "20260215_1100_dbaudit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (index_name, table_name) — all are DROP IF EXISTS for safety
_REDUNDANT = [
    ("ix_ar_content_id", "ar_content"),
    ("uq_ar_content_unique_id", "ar_content"),
    ("ix_ar_content_company_id", "ar_content"),
    ("ix_ar_content_project_id", "ar_content"),
    ("ix_users_id", "users"),
    ("ix_videos_id", "videos"),
    ("ix_projects_id", "projects"),
    ("ix_companies_id", "companies"),
]


def upgrade() -> None:
    for idx_name, _table in _REDUNDANT:
        op.execute(sa.text(f"DROP INDEX IF EXISTS {idx_name}"))


def downgrade() -> None:
    # Re-create the redundant indexes (they are harmless, just wasteful)
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_ar_content_id ON ar_content (id)"))
    op.execute(sa.text("CREATE UNIQUE INDEX IF NOT EXISTS uq_ar_content_unique_id ON ar_content (unique_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_ar_content_company_id ON ar_content (company_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_ar_content_project_id ON ar_content (project_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_users_id ON users (id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_videos_id ON videos (id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_projects_id ON projects (id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_companies_id ON companies (id)"))
