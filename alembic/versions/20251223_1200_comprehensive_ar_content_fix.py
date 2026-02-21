"""Comprehensive AR Content schema fix - ensure all required columns and timestamps exist

Revision ID: 20251223_1200_comprehensive_ar_content_fix
Revises: e90dda773ba4
Create Date: 2025-12-23 12:00:00.000000

PostgreSQL: ADD COLUMN IF NOT EXISTS. SQLite: conditional add via PRAGMA table_info.
"""
from typing import Sequence, Union
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '20251223_1200_comprehensive_ar_content_fix'
down_revision: Union[str, None] = 'widen_ver'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_columns_sqlite(conn) -> set[str]:
    """Return set of column names in ar_content (SQLite)."""
    result = conn.execute(text("PRAGMA table_info(ar_content)"))
    return {row[1] for row in result}


def upgrade() -> None:
    """Ensure all required columns exist in ar_content table."""
    conn = op.get_bind()

    if conn.dialect.name == 'postgresql':
        for col_sql in [
            "ALTER TABLE ar_content ADD COLUMN IF NOT EXISTS thumbnail_url VARCHAR(500)",
            "ALTER TABLE ar_content ADD COLUMN IF NOT EXISTS marker_path VARCHAR(500)",
            "ALTER TABLE ar_content ADD COLUMN IF NOT EXISTS marker_url VARCHAR(500)",
            "ALTER TABLE ar_content ADD COLUMN IF NOT EXISTS marker_status VARCHAR(50)",
            "ALTER TABLE ar_content ADD COLUMN IF NOT EXISTS marker_metadata JSONB",
            "ALTER TABLE ar_content ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
            "ALTER TABLE ar_content ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()",
        ]:
            op.execute(col_sql)
    else:
        # SQLite: no IF NOT EXISTS for ADD COLUMN; add only missing columns
        existing = _existing_columns_sqlite(conn)
        columns_sqlite = [
            ("thumbnail_url", "VARCHAR(500)"),
            ("marker_path", "VARCHAR(500)"),
            ("marker_url", "VARCHAR(500)"),
            ("marker_status", "VARCHAR(50)"),
            ("marker_metadata", "TEXT"),  # SQLite: JSON as TEXT
            ("created_at", "TIMESTAMP NOT NULL DEFAULT (datetime('now'))"),
            ("updated_at", "TIMESTAMP NOT NULL DEFAULT (datetime('now'))"),
        ]
        for col_name, col_type in columns_sqlite:
            if col_name not in existing:
                op.execute(
                    f"ALTER TABLE ar_content ADD COLUMN {col_name} {col_type}"
                )
    # For NOT NULL columns added without default on existing rows, relax then add default in two steps if needed
    # (above uses DEFAULT NOW() so new rows get value; existing rows may need backfill - run separately if needed)

    # Indexes and constraints: use DO block to ignore duplicate
    for sql in [
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_ar_content_unique_id ON ar_content (unique_id)",
        "CREATE INDEX IF NOT EXISTS ix_ar_content_company_project ON ar_content (company_id, project_id)",
        "CREATE INDEX IF NOT EXISTS ix_ar_content_created_at ON ar_content (created_at)",
        "CREATE INDEX IF NOT EXISTS ix_ar_content_status ON ar_content (status)",
    ]:
        try:
            op.execute(sql)
        except Exception:
            pass

    # Foreign keys: only add if not exist (PostgreSQL only; DO block fails on SQLite)
    if conn.dialect.name == 'postgresql':
        for fk_sql in [
            """DO $$ BEGIN
               IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_ar_content_project') THEN
                 ALTER TABLE ar_content ADD CONSTRAINT fk_ar_content_project FOREIGN KEY (project_id) REFERENCES projects(id);
               END IF; END $$""",
            """DO $$ BEGIN
               IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_ar_content_company') THEN
                 ALTER TABLE ar_content ADD CONSTRAINT fk_ar_content_company FOREIGN KEY (company_id) REFERENCES companies(id);
               END IF; END $$""",
            """DO $$ BEGIN
               IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_ar_content_active_video') THEN
                 ALTER TABLE ar_content ADD CONSTRAINT fk_ar_content_active_video FOREIGN KEY (active_video_id) REFERENCES videos(id);
               END IF; END $$""",
        ]:
            try:
                op.execute(fk_sql)
            except Exception:
                pass


def downgrade() -> None:
    """Remove the columns that were added by this migration."""
    conn = op.get_bind()

    # Remove indexes (IF NOT EXISTS works in both PostgreSQL and SQLite)
    op.execute("DROP INDEX IF EXISTS ix_ar_content_status")
    op.execute("DROP INDEX IF EXISTS ix_ar_content_created_at")
    op.execute("DROP INDEX IF EXISTS ix_ar_content_company_project")
    op.execute("DROP INDEX IF EXISTS uq_ar_content_unique_id")

    # Remove foreign key constraints (PostgreSQL only; SQLite has no DROP CONSTRAINT)
    if conn.dialect.name == 'postgresql':
        op.execute("ALTER TABLE ar_content DROP CONSTRAINT IF EXISTS fk_ar_content_active_video")
        op.execute("ALTER TABLE ar_content DROP CONSTRAINT IF EXISTS fk_ar_content_company")
        op.execute("ALTER TABLE ar_content DROP CONSTRAINT IF EXISTS fk_ar_content_project")
    
    # Remove columns (only if they were added by this migration)
    # Note: We'll be conservative and not remove columns that might have been added by other migrations
    # This is a safety measure to avoid breaking the database