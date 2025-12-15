"""remove_enum_types_and_simplify_user_role

Revision ID: 5eac18e27a8d
Revises: 673223c13c4b
Create Date: 2025-12-15 19:20:35.007406

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5eac18e27a8d'
down_revision: Union[str, None] = '673223c13c4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # First, alter the role column to remove the default value and change type
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.alter_column('users', 'role', type_=sa.String(50), existing_type=postgresql.ENUM('admin', 'manager', 'viewer', name='user_role'))
    
    # Drop the ENUM types with CASCADE
    op.execute("DROP TYPE IF EXISTS user_role CASCADE")
    op.execute("DROP TYPE IF EXISTS notification_type CASCADE")


def downgrade() -> None:
    # Recreate the ENUM types
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE user_role AS ENUM ('admin', 'manager', 'viewer');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE notification_type AS ENUM ('email', 'telegram', 'system', 'sms');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Change the role column back to ENUM
    op.alter_column('users', 'role', type_=postgresql.ENUM('admin', 'manager', 'viewer', name='user_role'), existing_type=sa.String(50))
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'viewer'")