"""Initial database schema with users and demo data

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-12-08 14:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial schema with users, storage, and companies"""
    
    # 1. Create enum for user roles (check if exists first)
    conn = op.get_bind()
    res = conn.execute(sa.text("SELECT 1 FROM pg_type WHERE typname='userrole'"))
    if res.first() is None:
        op.execute(sa.text("CREATE TYPE userrole AS ENUM ('ADMIN', 'MANAGER', 'VIEWER')"))
    
    # 2. Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default="'ADMIN'"),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('login_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    
    # 3. Insert default admin user (password: admin123, using SHA256 fallback)
    op.execute(sa.text("""
        INSERT INTO users (email, hashed_password, full_name, role, is_active, login_attempts, created_at, updated_at)
        VALUES (
            'admin@vertexar.com',
            'sha256$240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',
            'Vertex AR Admin',
            'ADMIN',
            true,
            0,
            now(),
            now()
        )
    """))
    
    # 4. Create storage_connections table
    op.create_table(
        'storage_connections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('credentials', postgresql.JSONB(), nullable=True, server_default='{}'),
        sa.Column('base_path', sa.String(500), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_tested_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('test_status', sa.String(50), nullable=True),
        sa.Column('test_error', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_storage_connections_id'), 'storage_connections', ['id'], unique=False)
    
    # 5. Insert default Vertex AR storage connection (local disk)
    op.execute(sa.text("""
        INSERT INTO storage_connections (name, provider, base_path, is_default, is_active, created_at, updated_at)
        VALUES (
            'Vertex AR Local Storage',
            'local_disk',
            '/app/storage/content',
            true,
            true,
            now(),
            now()
        )
    """))
    
    # 6. Create companies table
    op.create_table(
        'companies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False),
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('contact_phone', sa.String(50), nullable=True),
        sa.Column('telegram_chat_id', sa.String(100), nullable=True),
        sa.Column('storage_connection_id', sa.Integer(), nullable=True),
        sa.Column('storage_path', sa.String(500), nullable=True),
        sa.Column('subscription_tier', sa.String(50), nullable=False, server_default='basic'),
        sa.Column('storage_quota_gb', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('storage_used_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('projects_limit', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('subscription_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['storage_connection_id'], ['storage_connections.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_companies_id'), 'companies', ['id'], unique=False)
    op.create_index(op.f('ix_companies_slug'), 'companies', ['slug'], unique=False)
    
    # 7. Insert default Vertex AR company
    op.execute(sa.text("""
        INSERT INTO companies (name, slug, storage_connection_id, storage_path, subscription_tier, 
                              storage_quota_gb, projects_limit, is_active, is_default, notes, 
                              created_at, updated_at)
        SELECT
            'Vertex AR',
            'vertex-ar',
            id,
            '/',
            'premium',
            100,
            1000,
            true,
            true,
            'Основная компания Vertex AR. Локальное хранилище.',
            now(),
            now()
        FROM storage_connections
        WHERE name = 'Vertex AR Local Storage'
    """))


def downgrade() -> None:
    """Drop all tables and enums"""
    op.drop_index(op.f('ix_companies_slug'), table_name='companies')
    op.drop_index(op.f('ix_companies_id'), table_name='companies')
    op.drop_table('companies')
    op.drop_index(op.f('ix_storage_connections_id'), table_name='storage_connections')
    op.drop_table('storage_connections')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
    op.execute(sa.text('DROP TYPE userrole'))
