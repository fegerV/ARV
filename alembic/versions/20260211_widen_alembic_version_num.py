"""Widen alembic_version.version_num for long revision IDs

Revision ID: widen_ver
Revises: e90dda773ba4
Create Date: 2026-02-11

Alembic default is VARCHAR(32); revision 20251223_1200_comprehensive_ar_content_fix is longer.
SQLite: no-op (no length limit on TEXT); PostgreSQL: ALTER COLUMN.
"""
from typing import Sequence, Union
from alembic import op

revision: str = 'widen_ver'
down_revision: Union[str, None] = 'e90dda773ba4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        op.execute(
            "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64)"
        )
    # SQLite: no-op — TEXT has no length limit, long revision IDs work as-is


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        op.execute(
            "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(32)"
        )
