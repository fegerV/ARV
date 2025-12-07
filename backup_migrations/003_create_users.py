"""Create users table

Revision ID: 003_create_users
Revises: 20251205_thumbnails
Create Date: 2025-12-05 14:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_create_users'
down_revision = '0015_create_demo_data'  # Fixed dependency chain
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if userrole enum exists
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT 1 FROM pg_type WHERE typname = 'userrole'
    """))
    
    # Create enum type if it doesn't exist
    if not result.fetchone():
        op.execute("CREATE TYPE userrole AS ENUM ('ADMIN', 'MANAGER', 'VIEWER')")
    
    # Check if users table exists
    result = conn.execute(sa.text("""
        SELECT 1 FROM information_schema.tables WHERE table_name = 'users'
    """))
    
    # Create users table if it doesn't exist
    if not result.fetchone():
        op.execute("""
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                email VARCHAR NOT NULL,
                hashed_password VARCHAR NOT NULL,
                full_name VARCHAR NOT NULL,
                role userrole NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT true,
                last_login_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                login_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until TIMESTAMP WITH TIME ZONE
            )
        """)
        
        op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    
    # Check if default admin user exists before inserting
    result = conn.execute(sa.text("""
        SELECT 1 FROM users WHERE email = 'admin@vertexar.com'
    """))
    
    if not result.fetchone():
        # Insert default admin user (password: admin123)
        # IMPORTANT: Change password in production!
        op.execute("""
            INSERT INTO users (email, hashed_password, full_name, role, is_active, login_attempts)
            VALUES (
                'admin@vertexar.com',
                '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIxF2PQaDi',  -- admin123
                'Vertex AR Admin',
                'ADMIN',
                true,
                0
            )
        """)


def downgrade() -> None:
    # Check if users table exists before dropping
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT 1 FROM information_schema.tables WHERE table_name = 'users'
    """))
    
    if result.fetchone():
        op.drop_index(op.f('ix_users_email'), table_name='users')
        op.drop_index(op.f('ix_users_id'), table_name='users')
        op.drop_table('users')
    
    # Check if userrole enum exists before dropping
    result = conn.execute(sa.text("""
        SELECT 1 FROM pg_type WHERE typname = 'userrole'
    """))
    
    if result.fetchone():
        op.execute('DROP TYPE userrole')