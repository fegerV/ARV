"""Add company_id and is_super_admin to users, user_id to notifications.

Revision ID: 20260819_2000_add_user_company_and_notification_user
Revises: 20260422_1200_nullable_vrs_legacy
Create Date: 2026-08-19 20:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text


revision: str = "20260819_2000_add_user_company_and_notification_user"
down_revision: Union[str, None] = "20260422_1200_nullable_vrs_legacy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    return column_name in {column["name"] for column in inspect(bind).get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        if not _has_column("users", "company_id"):
            op.execute(
                text(
                    "ALTER TABLE users ADD COLUMN company_id INTEGER REFERENCES companies(id)"
                )
            )
        if not _has_column("users", "is_super_admin"):
            op.execute(
                text(
                    "ALTER TABLE users ADD COLUMN is_super_admin BOOLEAN DEFAULT FALSE NOT NULL"
                )
            )
        if not _has_column("notifications", "user_id"):
            op.execute(
                text(
                    "ALTER TABLE notifications ADD COLUMN user_id INTEGER REFERENCES users(id)"
                )
            )
    else:
        with op.batch_alter_table("users") as batch_op:
            if not _has_column("users", "company_id"):
                batch_op.add_column(sa.Column("company_id", sa.Integer, nullable=True))
            if not _has_column("users", "is_super_admin"):
                batch_op.add_column(sa.Column("is_super_admin", sa.Boolean, nullable=False, server_default=sa.text("0")))

        with op.batch_alter_table("notifications") as batch_op:
            if not _has_column("notifications", "user_id"):
                batch_op.add_column(sa.Column("user_id", sa.Integer, nullable=True))


def downgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        if _has_column("notifications", "user_id"):
            op.execute(text("ALTER TABLE notifications DROP COLUMN user_id"))
        if _has_column("users", "is_super_admin"):
            op.execute(text("ALTER TABLE users DROP COLUMN is_super_admin"))
        if _has_column("users", "company_id"):
            op.execute(text("ALTER TABLE users DROP COLUMN company_id"))
    else:
        with op.batch_alter_table("notifications") as batch_op:
            if _has_column("notifications", "user_id"):
                batch_op.drop_column("user_id")

        with op.batch_alter_table("users") as batch_op:
            if _has_column("users", "is_super_admin"):
                batch_op.drop_column("is_super_admin")
            if _has_column("users", "company_id"):
                batch_op.drop_column("company_id")
