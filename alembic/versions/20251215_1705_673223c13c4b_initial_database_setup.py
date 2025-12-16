"""initial_database_setup

Revision ID: 673223c13c4b
Revises: 
Create Date: 2025-12-15 17:05:22.034136

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '673223c13c4b'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable UUID extension
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    
    # Create ENUM types
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
    
    # 1. USERS TABLE
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('role', postgresql.ENUM('admin', 'manager', 'viewer', name='user_role', create_type=False), nullable=False, server_default='viewer'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('login_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('locked_until', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for users
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_role', 'users', ['role'])
    op.create_index('ix_users_is_active', 'users', ['is_active'])
    op.create_index('ix_users_created_at', 'users', ['created_at'])
    
    # 2. COMPANIES TABLE
    op.create_table('companies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('contact_phone', sa.String(length=50), nullable=True),
        sa.Column('telegram_chat_id', sa.String(length=100), nullable=True),
        sa.Column('storage_type', sa.String(length=50), nullable=True, server_default='local'),
        sa.Column('yandex_disk_folder_id', sa.String(length=255), nullable=True),
        sa.Column('content_types', sa.String(length=255), nullable=True),
        sa.Column('backup_provider', sa.String(length=50), nullable=True),
        sa.Column('backup_remote_path', sa.String(length=500), nullable=True),
        sa.Column('storage_connection_id', sa.Integer(), nullable=True),
        sa.Column('storage_path', sa.String(length=500), nullable=True),
        sa.Column('subscription_tier', sa.String(length=50), nullable=True, server_default='basic'),
        sa.Column('storage_quota_gb', sa.Integer(), nullable=True, server_default='10'),
        sa.Column('storage_used_bytes', sa.BigInteger(), nullable=True, server_default='0'),
        sa.Column('projects_limit', sa.Integer(), nullable=True, server_default='50'),
        sa.Column('subscription_expires_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('is_default', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for companies
    op.create_index('ix_companies_name', 'companies', ['name'])
    op.create_index('ix_companies_slug', 'companies', ['slug'])
    op.create_index('ix_companies_storage_type', 'companies', ['storage_type'])
    op.create_index('ix_companies_is_active', 'companies', ['is_active'])
    op.create_index('ix_companies_created_at', 'companies', ['created_at'])
    
    # 3. STORAGE_CONNECTIONS TABLE
    op.create_table('storage_connections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('credentials', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('base_path', sa.String(length=500), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('last_tested_at', sa.DateTime(), nullable=True),
        sa.Column('test_status', sa.String(length=50), nullable=True),
        sa.Column('test_error', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Indexes for storage_connections
    op.create_index('ix_storage_connections_provider', 'storage_connections', ['provider'])
    op.create_index('ix_storage_connections_is_active', 'storage_connections', ['is_active'])
    op.create_index('ix_storage_connections_created_at', 'storage_connections', ['created_at'])
    
    # 4. PROJECTS TABLE
    op.create_table('projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='active'),
        sa.Column('subscription_end', sa.DateTime(), nullable=True),
        sa.Column('lifecycle_status', sa.String(length=50), nullable=True, server_default='active'),
        sa.Column('notified_7d', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('notified_24h', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('notified_expired', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'slug')
    )
    
    # Indexes for projects
    op.create_index('ix_projects_company_id', 'projects', ['company_id'])
    op.create_index('ix_projects_status', 'projects', ['status'])
    op.create_index('ix_projects_subscription_end', 'projects', ['subscription_end'])
    op.create_index('ix_projects_created_at', 'projects', ['created_at'])
    
    # 5. FOLDERS TABLE
    op.create_table('folders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('folder_path', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.String(length=50), nullable=True, server_default='active'),
        sa.Column('sort_order', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['parent_id'], ['folders.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'name', 'parent_id')
    )
    
    # Indexes for folders
    op.create_index('ix_folders_project_id', 'folders', ['project_id'])
    op.create_index('ix_folders_parent_id', 'folders', ['parent_id'])
    op.create_index('ix_folders_is_active', 'folders', ['is_active'])
    op.create_index('ix_folders_created_at', 'folders', ['created_at'])
    
    # 6. CLIENTS TABLE
    op.create_table('clients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('address', sa.String(length=500), nullable=True),
        sa.Column('notes', sa.String(length=1000), nullable=True),
        sa.Column('is_active', sa.String(length=50), nullable=True, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for clients
    op.create_index('ix_clients_company_id', 'clients', ['company_id'])
    op.create_index('ix_clients_email', 'clients', ['email'])
    op.create_index('ix_clients_name', 'clients', ['name'])
    
    # 7. AR_CONTENT TABLE
    op.create_table('ar_content',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('unique_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('image_path', sa.String(length=500), nullable=False),
        sa.Column('image_url', sa.String(length=500), nullable=True),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        sa.Column('video_path', sa.String(length=500), nullable=True),
        sa.Column('video_url', sa.String(length=500), nullable=True),
        sa.Column('qr_code_path', sa.String(length=500), nullable=True),
        sa.Column('qr_code_url', sa.String(length=500), nullable=True),
        sa.Column('preview_url', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('views_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_viewed_at', sa.DateTime(), nullable=True),
        sa.Column('content_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('unique_id')
    )
    
    # Indexes for ar_content
    op.create_index('ix_ar_content_unique_id', 'ar_content', ['unique_id'])
    op.create_index('ix_ar_content_project_id', 'ar_content', ['project_id'])
    op.create_index('ix_ar_content_company_id', 'ar_content', ['company_id'])
    op.create_index('ix_ar_content_company_project', 'ar_content', ['company_id', 'project_id'])
    op.create_index('ix_ar_content_is_active', 'ar_content', ['is_active'])
    op.create_index('ix_ar_content_created_at', 'ar_content', ['created_at'])
    
    # 8. VIDEOS TABLE
    op.create_table('videos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ar_content_id', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('public_url', sa.String(length=500), nullable=True),
        sa.Column('video_path', sa.String(length=500), nullable=True),
        sa.Column('video_url', sa.String(length=500), nullable=True),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('duration', sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='active'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('schedule_start', sa.DateTime(), nullable=True),
        sa.Column('schedule_end', sa.DateTime(), nullable=True),
        sa.Column('rotation_type', sa.String(length=50), nullable=True),
        sa.Column('rotation_order', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['ar_content_id'], ['ar_content.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for videos
    op.create_index('ix_videos_ar_content_id', 'videos', ['ar_content_id'])
    op.create_index('ix_videos_status', 'videos', ['status'])
    op.create_index('ix_videos_rotation_type', 'videos', ['rotation_type'])
    op.create_index('ix_videos_schedule_start', 'videos', ['schedule_start'])
    op.create_index('ix_videos_schedule_end', 'videos', ['schedule_end'])
    op.create_index('ix_videos_created_at', 'videos', ['created_at'])
    
    # 9. EMAIL_QUEUE TABLE
    op.create_table('email_queue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recipient_to', sa.String(length=255), nullable=False),
        sa.Column('recipient_cc', sa.String(length=255), nullable=True),
        sa.Column('recipient_bcc', sa.String(length=255), nullable=True),
        sa.Column('subject', sa.String(length=500), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('html', sa.Text(), nullable=True),
        sa.Column('template_id', sa.String(length=100), nullable=True),
        sa.Column('variables', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='pending'),
        sa.Column('attempts', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('max_attempts', sa.Integer(), nullable=True, server_default='3'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True, server_default='5'),
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for email_queue
    op.create_index('ix_email_queue_status', 'email_queue', ['status'])
    op.create_index('ix_email_queue_priority', 'email_queue', ['priority'])
    op.create_index('ix_email_queue_scheduled_at', 'email_queue', ['scheduled_at'])
    op.create_index('ix_email_queue_created_at', 'email_queue', ['created_at'])
    
    # 10. NOTIFICATIONS TABLE
    op.create_table('notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('type', postgresql.ENUM('email', 'telegram', 'system', 'sms', name='notification_type', create_type=False), nullable=True, server_default='system'),
        sa.Column('priority', sa.String(length=50), nullable=True, server_default='normal'),
        sa.Column('is_read', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('service_name', sa.String(length=100), nullable=True),
        sa.Column('event_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('group_id', sa.String(length=100), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=True, server_default='3'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for notifications
    op.create_index('ix_notifications_company_id', 'notifications', ['company_id'])
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_type', 'notifications', ['type'])
    op.create_index('ix_notifications_is_read', 'notifications', ['is_read'])
    op.create_index('ix_notifications_created_at', 'notifications', ['created_at'])
    op.create_index('ix_notifications_group_id', 'notifications', ['group_id'])
    
    # 11. AUDIT_LOG TABLE
    op.create_table('audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('changes', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('field_name', sa.String(length=100), nullable=True),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('actor_email', sa.String(length=255), nullable=True),
        sa.Column('actor_ip', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.Column('request_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for audit_log
    op.create_index('ix_audit_log_entity', 'audit_log', ['entity_type', 'entity_id'])
    op.create_index('ix_audit_log_action', 'audit_log', ['action'])
    op.create_index('ix_audit_log_actor_id', 'audit_log', ['actor_id'])
    op.create_index('ix_audit_log_created_at', 'audit_log', ['created_at'])
    op.create_index('ix_audit_log_session_id', 'audit_log', ['session_id'])
    
    # Insert default admin user
    op.execute("""
        INSERT INTO users (email, hashed_password, full_name, role, is_active)
        VALUES (
            'admin@vertexar.com',
            '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIxF2PQaDi',  -- admin123
            'Vertex AR Admin',
            'admin',
            true
        )
    """)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('audit_log')
    op.drop_table('notifications')
    op.drop_table('email_queue')
    op.drop_table('videos')
    op.drop_table('ar_content')
    op.drop_table('clients')
    op.drop_table('folders')
    op.drop_table('projects')
    op.drop_table('storage_connections')
    op.drop_table('companies')
    op.drop_table('users')
    
    # Drop indexes
    op.drop_index('ix_audit_log_session_id', table_name='audit_log')
    op.drop_index('ix_audit_log_created_at', table_name='audit_log')
    op.drop_index('ix_audit_log_actor_id', table_name='audit_log')
    op.drop_index('ix_audit_log_action', table_name='audit_log')
    op.drop_index('ix_audit_log_entity', table_name='audit_log')
    op.drop_index('ix_notifications_group_id', table_name='notifications')
    op.drop_index('ix_notifications_created_at', table_name='notifications')
    op.drop_index('ix_notifications_is_read', table_name='notifications')
    op.drop_index('ix_notifications_type', table_name='notifications')
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_index('ix_notifications_company_id', table_name='notifications')
    op.drop_index('ix_email_queue_created_at', table_name='email_queue')
    op.drop_index('ix_email_queue_scheduled_at', table_name='email_queue')
    op.drop_index('ix_email_queue_priority', table_name='email_queue')
    op.drop_index('ix_email_queue_status', table_name='email_queue')
    op.drop_index('ix_videos_created_at', table_name='videos')
    op.drop_index('ix_videos_schedule_end', table_name='videos')
    op.drop_index('ix_videos_schedule_start', table_name='videos')
    op.drop_index('ix_videos_rotation_type', table_name='videos')
    op.drop_index('ix_videos_status', table_name='videos')
    op.drop_index('ix_videos_ar_content_id', table_name='videos')
    op.drop_index('ix_ar_content_created_at', table_name='ar_content')
    op.drop_index('ix_ar_content_is_active', table_name='ar_content')
    op.drop_index('ix_ar_content_company_project', table_name='ar_content')
    op.drop_index('ix_ar_content_company_id', table_name='ar_content')
    op.drop_index('ix_ar_content_project_id', table_name='ar_content')
    op.drop_index('ix_ar_content_unique_id', table_name='ar_content')
    op.drop_index('ix_clients_name', table_name='clients')
    op.drop_index('ix_clients_email', table_name='clients')
    op.drop_index('ix_clients_company_id', table_name='clients')
    op.drop_index('ix_folders_created_at', table_name='folders')
    op.drop_index('ix_folders_is_active', table_name='folders')
    op.drop_index('ix_folders_parent_id', table_name='folders')
    op.drop_index('ix_folders_project_id', table_name='folders')
    op.drop_index('ix_projects_created_at', table_name='projects')
    op.drop_index('ix_projects_subscription_end', table_name='projects')
    op.drop_index('ix_projects_status', table_name='projects')
    op.drop_index('ix_projects_company_id', table_name='projects')
    op.drop_index('ix_storage_connections_created_at', table_name='storage_connections')
    op.drop_index('ix_storage_connections_is_active', table_name='storage_connections')
    op.drop_index('ix_storage_connections_provider', table_name='storage_connections')
    op.drop_index('ix_companies_created_at', table_name='companies')
    op.drop_index('ix_companies_is_active', table_name='companies')
    op.drop_index('ix_companies_storage_type', table_name='companies')
    op.drop_index('ix_companies_slug', table_name='companies')
    op.drop_index('ix_companies_name', table_name='companies')
    op.drop_index('ix_users_created_at', table_name='users')
    op.drop_index('ix_users_is_active', table_name='users')
    op.drop_index('ix_users_role', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    
    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS notification_type")
    op.execute("DROP TYPE IF EXISTS user_role")
    
    # Drop extension
    op.execute("DROP EXTENSION IF EXISTS \"uuid-ossp\"")