"""Make legacy rotation schedule columns nullable.

Revision ID: 20260422_1200_nullable_vrs_legacy
Revises: 20260219_1000_devmodel
Create Date: 2026-04-22 12:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text


revision: str = "20260422_1200_nullable_vrs_legacy"
down_revision: Union[str, None] = "20260219_1000_devmodel"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    return column_name in {column["name"] for column in inspect(bind).get_columns(table_name)}


def upgrade() -> None:
    """Old schemas kept unused name/schedule_type as NOT NULL."""
    bind = op.get_bind()

    if _has_column("video_rotation_schedules", "name"):
        op.execute(
            text(
                "UPDATE video_rotation_schedules "
                "SET name = 'Rotation schedule' "
                "WHERE name IS NULL OR name = ''"
            )
        )
    if _has_column("video_rotation_schedules", "schedule_type"):
        op.execute(
            text(
                "UPDATE video_rotation_schedules "
                "SET schedule_type = COALESCE(rotation_type, 'daily_cycle') "
                "WHERE schedule_type IS NULL OR schedule_type = ''"
            )
        )

    if bind.dialect.name == "postgresql":
        if _has_column("video_rotation_schedules", "name"):
            op.alter_column(
                "video_rotation_schedules",
                "name",
                existing_type=sa.String(length=255),
                nullable=True,
            )
        if _has_column("video_rotation_schedules", "schedule_type"):
            op.alter_column(
                "video_rotation_schedules",
                "schedule_type",
                existing_type=sa.String(length=50),
                nullable=True,
            )
    else:
        with op.batch_alter_table("video_rotation_schedules") as batch_op:
            if _has_column("video_rotation_schedules", "name"):
                batch_op.alter_column(
                    "name",
                    existing_type=sa.String(length=255),
                    nullable=True,
                )
            if _has_column("video_rotation_schedules", "schedule_type"):
                batch_op.alter_column(
                    "schedule_type",
                    existing_type=sa.String(length=50),
                    nullable=True,
                )


def downgrade() -> None:
    bind = op.get_bind()

    if _has_column("video_rotation_schedules", "name"):
        op.execute(
            text(
                "UPDATE video_rotation_schedules "
                "SET name = 'Rotation schedule' "
                "WHERE name IS NULL OR name = ''"
            )
        )
    if _has_column("video_rotation_schedules", "schedule_type"):
        op.execute(
            text(
                "UPDATE video_rotation_schedules "
                "SET schedule_type = COALESCE(rotation_type, 'daily_cycle') "
                "WHERE schedule_type IS NULL OR schedule_type = ''"
            )
        )

    if bind.dialect.name == "postgresql":
        if _has_column("video_rotation_schedules", "name"):
            op.alter_column(
                "video_rotation_schedules",
                "name",
                existing_type=sa.String(length=255),
                nullable=False,
            )
        if _has_column("video_rotation_schedules", "schedule_type"):
            op.alter_column(
                "video_rotation_schedules",
                "schedule_type",
                existing_type=sa.String(length=50),
                nullable=False,
            )
    else:
        with op.batch_alter_table("video_rotation_schedules") as batch_op:
            if _has_column("video_rotation_schedules", "name"):
                batch_op.alter_column(
                    "name",
                    existing_type=sa.String(length=255),
                    nullable=False,
                )
            if _has_column("video_rotation_schedules", "schedule_type"):
                batch_op.alter_column(
                    "schedule_type",
                    existing_type=sa.String(length=50),
                    nullable=False,
                )
