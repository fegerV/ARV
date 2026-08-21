"""Add database-level integrity constraints.

Revision ID: 20260821_1230_add_integrity_constraints
Revises: 20260821_1200_drop_unused_models
Create Date: 2026-08-21 12:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260821_1230_add_integrity_constraints"
down_revision: Union[str, None] = "20260821_1200_drop_unused_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_sqlite() -> bool:
    context = op.get_context()
    return context.dialect.name == "sqlite"


def upgrade() -> None:
    if _is_sqlite():
        return

    op.execute(
        sa.text(
            "ALTER TABLE ar_content "
            "ADD CONSTRAINT ck_ar_content_active_video_belongs_to_content "
            "CHECK (active_video_id IS NULL OR EXISTS ("
            "  SELECT 1 FROM videos "
            "  WHERE videos.id = ar_content.active_video_id "
            "    AND videos.ar_content_id = ar_content.id"
            "))"
        )
    )

    op.execute(
        sa.text(
            "ALTER TABLE users "
            "ADD CONSTRAINT ck_user_role_valid "
            "CHECK (role IN ('admin', 'editor', 'user'))"
        )
    )


def downgrade() -> None:
    if _is_sqlite():
        return

    op.execute(sa.text("ALTER TABLE ar_content DROP CONSTRAINT ck_ar_content_active_video_belongs_to_content"))
    op.execute(sa.text("ALTER TABLE users DROP CONSTRAINT ck_user_role_valid"))
