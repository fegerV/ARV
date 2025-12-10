"""Complete initial migration for PostgreSQL database

This migration creates all required tables for the Vertex AR B2B Platform:
- Basic tables: users, companies
- Content hierarchy: projects, folders, portraits, videos
- Orders and clients: clients, orders
- Storage and configuration: storage_connections
- Email and notifications: email_queue, notifications
- Audit: audit_log

Revision ID: 20251218_initial_complete_migration
Revises: 20251210_add_thumbnail_url_fields
Create Date: 2025-12-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20251218_initial_complete_migration'
down_revision = '20251210_add_thumbnail_url_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if tables already exist to avoid errors
    existing_tables = inspector.get_table_names()
    
    # 1. Update companies table with new fields
    if 'companies' in existing_tables:
        # Add new storage fields to companies table
        company_columns = [col['name'] for col in inspector.get_columns('companies')]
        
        if 'storage_type' not in company_columns:
            op.add_column('companies', sa.Column('storage_type', sa.String(length=50), nullable=True, server_default='local'))
        if 'yandex_disk_folder_id' not in company_columns:
            op.add_column('companies', sa.Column('yandex_disk_folder_id', sa.String(length=255), nullable=True))
        if 'content_types' not in company_columns:
            op.add_column('companies', sa.Column('content_types', sa.String(length=255), nullable=True))
        if 'backup_provider' not in company_columns:
            op.add_column('companies', sa.Column('backup_provider', sa.String(length=50), nullable=True))
        if 'backup_remote_path' not in company_columns:
            op.add_column('companies', sa.Column('backup_remote_path', sa.String(length=500), nullable=True))
    
    # 2. Update projects table with new fields
    if 'projects' in existing_tables:
        project_columns = [col['name'] for col in inspector.get_columns('projects')]
        
        if 'subscription_end' not in project_columns:
            op.add_column('projects', sa.Column('subscription_end', sa.DateTime(), nullable=True))
        if 'lifecycle_status' not in project_columns:
            op.add_column('projects', sa.Column('lifecycle_status', sa.String(length=50), nullable=True, server_default='active'))
        if 'notified_7d' not in project_columns:
            op.add_column('projects', sa.Column('notified_7d', sa.Boolean(), nullable=True, server_default=False))
        if 'notified_24h' not in project_columns:
            op.add_column('projects', sa.Column('notified_24h', sa.Boolean(), nullable=True, server_default=False))
        if 'notified_expired' not in project_columns:
            op.add_column('projects', sa.Column('notified_expired', sa.Boolean(), nullable=True, server_default=False))
        
        # Add company_id foreign key if not exists
        if 'company_id' not in project_columns:
            op.add_column('projects', sa.Column('company_id', sa.Integer(), nullable=False))
            op.create_foreign_key('fk_projects_company', 'projects', 'companies', ['company_id'], ['id'])
        
        # Add indexes for performance
        op.create_index('ix_projects_company_id', 'projects', ['company_id'])
        op.create_index('ix_projects_status', 'projects', ['status'])
        op.create_index('ix_projects_created_at', 'projects', ['created_at'])
    
    # 3. Create folders table
    if 'folders' not in existing_tables:
        op.create_table(
            'folders',
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
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_folders_project_id', 'folders', ['project_id'])
        op.create_index('ix_folders_parent_id', 'folders', ['parent_id'])
    
    # 4. Create clients table
    if 'clients' not in existing_tables:
        op.create_table(
            'clients',
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
            sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_clients_company_id', 'clients', ['company_id'])
        op.create_index('ix_clients_email', 'clients', ['email'])
    
    # 5. Create orders table
    if 'orders' not in existing_tables:
        op.create_table(
            'orders',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('company_id', sa.Integer(), nullable=False),
            sa.Column('client_id', sa.Integer(), nullable=True),
            sa.Column('order_number', sa.String(length=100), nullable=False),
            sa.Column('content_type', sa.String(length=100), nullable=False),
            sa.Column('status', sa.String(length=50), nullable=True, server_default='pending'),
            sa.Column('payment_status', sa.String(length=50), nullable=True, server_default='unpaid'),
            sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('currency', sa.String(length=10), nullable=True, server_default='USD'),
            sa.Column('subscription_end', sa.DateTime(), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
            sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('order_number')
        )
        op.create_index('ix_orders_company_id', 'orders', ['company_id'])
        op.create_index('ix_orders_client_id', 'orders', ['client_id'])
        op.create_index('ix_orders_status', 'orders', ['status'])
        op.create_index('ix_orders_created_at', 'orders', ['created_at'])
    
    # 6. Update portraits table with new fields
    if 'portraits' in existing_tables:
        portrait_columns = [col['name'] for col in inspector.get_columns('portraits')]
        
        # Add new fields
        if 'company_id' not in portrait_columns:
            op.add_column('portraits', sa.Column('company_id', sa.Integer(), nullable=False))
            op.create_foreign_key('fk_portraits_company', 'portraits', 'companies', ['company_id'], ['id'])
        
        if 'client_id' not in portrait_columns:
            op.add_column('portraits', sa.Column('client_id', sa.Integer(), nullable=True))
            op.create_foreign_key('fk_portraits_client', 'portraits', 'clients', ['client_id'], ['id'])
        
        if 'folder_id' not in portrait_columns:
            op.add_column('portraits', sa.Column('folder_id', sa.Integer(), nullable=True))
            op.create_foreign_key('fk_portraits_folder', 'portraits', 'folders', ['folder_id'], ['id'])
        
        if 'file_path' not in portrait_columns:
            op.add_column('portraits', sa.Column('file_path', sa.String(length=500), nullable=True))
        
        if 'public_url' not in portrait_columns:
            op.add_column('portraits', sa.Column('public_url', sa.String(length=500), nullable=True))
        
        if 'status' not in portrait_columns:
            op.add_column('portraits', sa.Column('status', sa.String(length=50), nullable=True, server_default='active'))
        
        if 'subscription_end' not in portrait_columns:
            op.add_column('portraits', sa.Column('subscription_end', sa.DateTime(), nullable=True))
        
        if 'lifecycle_status' not in portrait_columns:
            op.add_column('portraits', sa.Column('lifecycle_status', sa.String(length=50), nullable=True, server_default='active'))
        
        if 'notified_7d' not in portrait_columns:
            op.add_column('portraits', sa.Column('notified_7d', sa.Boolean(), nullable=True, server_default=False))
        
        if 'notified_24h' not in portrait_columns:
            op.add_column('portraits', sa.Column('notified_24h', sa.Boolean(), nullable=True, server_default=False))
        
        if 'notified_expired' not in portrait_columns:
            op.add_column('portraits', sa.Column('notified_expired', sa.Boolean(), nullable=True, server_default=False))
        
        # Add indexes
        op.create_index('ix_portraits_company_id', 'portraits', ['company_id'])
        op.create_index('ix_portraits_client_id', 'portraits', ['client_id'])
        op.create_index('ix_portraits_folder_id', 'portraits', ['folder_id'])
        op.create_index('ix_portraits_status', 'portraits', ['status'])
    
    # 7. Update videos table with new fields
    if 'videos' in existing_tables:
        video_columns = [col['name'] for col in inspector.get_columns('videos')]
        
        # Change ar_content_id to portrait_id if needed
        if 'ar_content_id' in video_columns and 'portrait_id' not in video_columns:
            # This is a complex migration - for now we'll add portrait_id as a new column
            op.add_column('videos', sa.Column('portrait_id', sa.Integer(), nullable=True))
            op.create_foreign_key('fk_videos_portrait', 'videos', 'portraits', ['portrait_id'], ['id'])
        elif 'portrait_id' not in video_columns:
            op.add_column('videos', sa.Column('portrait_id', sa.Integer(), nullable=False))
            op.create_foreign_key('fk_videos_portrait', 'videos', 'portraits', ['portrait_id'], ['id'])
        
        if 'file_path' not in video_columns:
            op.add_column('videos', sa.Column('file_path', sa.String(length=500), nullable=True))
        
        if 'public_url' not in video_columns:
            op.add_column('videos', sa.Column('public_url', sa.String(length=500), nullable=True))
        
        if 'status' not in video_columns:
            op.add_column('videos', sa.Column('status', sa.String(length=50), nullable=True, server_default='active'))
        
        if 'rotation_type' not in video_columns:
            op.add_column('videos', sa.Column('rotation_type', sa.String(length=50), nullable=True))
        
        # Add indexes
        op.create_index('ix_videos_portrait_id', 'videos', ['portrait_id'])
        op.create_index('ix_videos_status', 'videos', ['status'])
    
    # 8. Create email_queue table
    if 'email_queue' not in existing_tables:
        op.create_table(
            'email_queue',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('recipient_to', sa.String(length=255), nullable=False),
            sa.Column('recipient_cc', sa.String(length=255), nullable=True),
            sa.Column('recipient_bcc', sa.String(length=255), nullable=True),
            sa.Column('subject', sa.String(length=500), nullable=False),
            sa.Column('body', sa.Text(), nullable=False),
            sa.Column('html', sa.Text(), nullable=True),
            sa.Column('template_id', sa.String(length=100), nullable=True),
            sa.Column('variables', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")),
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
        op.create_index('ix_email_queue_status', 'email_queue', ['status'])
        op.create_index('ix_email_queue_priority', 'email_queue', ['priority'])
        op.create_index('ix_email_queue_scheduled_at', 'email_queue', ['scheduled_at'])
        op.create_index('ix_email_queue_created_at', 'email_queue', ['created_at'])
    
    # 9. Update notifications table if needed
    if 'notifications' in existing_tables:
        notification_columns = [col['name'] for col in inspector.get_columns('notifications')]
        
        # Add missing fields if needed
        if 'type' not in notification_columns and 'notification_type' in notification_columns:
            # Add type field as alias for notification_type
            op.add_column('notifications', sa.Column('type', sa.String(length=50), nullable=True))
        
        if 'priority' not in notification_columns:
            op.add_column('notifications', sa.Column('priority', sa.String(length=50), nullable=True, server_default='normal'))
        
        if 'source' not in notification_columns:
            op.add_column('notifications', sa.Column('source', sa.String(length=100), nullable=True))
        
        if 'service_name' not in notification_columns:
            op.add_column('notifications', sa.Column('service_name', sa.String(length=100), nullable=True))
        
        if 'event_data' not in notification_columns:
            op.add_column('notifications', sa.Column('event_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")))
        
        if 'group_id' not in notification_columns:
            op.add_column('notifications', sa.Column('group_id', sa.String(length=100), nullable=True))
        
        if 'processed_at' not in notification_columns:
            op.add_column('notifications', sa.Column('processed_at', sa.DateTime(), nullable=True))
        
        if 'read_at' not in notification_columns:
            op.add_column('notifications', sa.Column('read_at', sa.DateTime(), nullable=True))
        
        # Add indexes
        op.create_index('ix_notifications_company_id', 'notifications', ['company_id'])
        op.create_index('ix_notifications_type', 'notifications', ['notification_type'])
        op.create_index('ix_notifications_created_at', 'notifications', ['created_at'])
    
    # 10. Create audit_log table
    if 'audit_log' not in existing_tables:
        op.create_table(
            'audit_log',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('entity_type', sa.String(length=100), nullable=False),
            sa.Column('entity_id', sa.Integer(), nullable=False),
            sa.Column('action', sa.String(length=100), nullable=False),
            sa.Column('changes', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")),
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
        op.create_index('ix_audit_log_entity', 'audit_log', ['entity_type', 'entity_id'])
        op.create_index('ix_audit_log_action', 'audit_log', ['action'])
        op.create_index('ix_audit_log_actor_id', 'audit_log', ['actor_id'])
        op.create_index('ix_audit_log_created_at', 'audit_log', ['created_at'])
    
    # 11. Insert default admin user if not exists
    if 'users' in existing_tables:
        result = conn.execute(sa.text("SELECT COUNT(*) FROM users WHERE email = 'admin@vertexar.com'"))
        admin_exists = result.scalar() > 0
        
        if not admin_exists:
            # Insert default admin user (password: admin123)
            # IMPORTANT: Change password in production!
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
    
    # 12. Insert default storage connection if not exists
    if 'storage_connections' in existing_tables:
        result = conn.execute(sa.text("SELECT COUNT(*) FROM storage_connections WHERE name = 'default_local'"))
        storage_exists = result.scalar() > 0
        
        if not storage_exists:
            op.execute("""
                INSERT INTO storage_connections (name, provider, base_path, is_default, is_active, created_at, updated_at)
                VALUES (
                    'default_local',
                    'local_disk',
                    '/app/storage/content',
                    true,
                    true,
                    now(),
                    now()
                )
            """)


def downgrade() -> None:
    # Drop tables in reverse order of creation
    op.drop_table('audit_log')
    op.drop_table('email_queue')
    op.drop_table('orders')
    op.drop_table('clients')
    op.drop_table('folders')
    
    # Drop indexes and columns from existing tables
    op.drop_index('ix_videos_portrait_id', table_name='videos')
    op.drop_index('ix_videos_status', table_name='videos')
    if 'portrait_id' in [col['name'] for col in sa.inspect(op.get_bind()).get_columns('videos')]:
        op.drop_constraint('fk_videos_portrait', 'videos', type_='foreignkey')
        op.drop_column('videos', 'portrait_id')
    
    op.drop_index('ix_portraits_company_id', table_name='portraits')
    op.drop_index('ix_portraits_client_id', table_name='portraits')
    op.drop_index('ix_portraits_folder_id', table_name='portraits')
    op.drop_index('ix_portraits_status', table_name='portraits')
    
    # Drop new columns from portraits
    portrait_columns = [col['name'] for col in sa.inspect(op.get_bind()).get_columns('portraits')]
    new_portrait_columns = ['company_id', 'client_id', 'folder_id', 'file_path', 'public_url', 
                           'status', 'subscription_end', 'lifecycle_status', 'notified_7d', 
                           'notified_24h', 'notified_expired']
    for col in new_portrait_columns:
        if col in portrait_columns:
            op.drop_column('portraits', col)
    
    # Drop new columns from projects
    project_columns = [col['name'] for col in sa.inspect(op.get_bind()).get_columns('projects')]
    new_project_columns = ['subscription_end', 'lifecycle_status', 'notified_7d', 'notified_24h', 'notified_expired']
    for col in new_project_columns:
        if col in project_columns:
            op.drop_column('projects', col)
    
    # Drop new columns from companies
    company_columns = [col['name'] for col in sa.inspect(op.get_bind()).get_columns('companies')]
    new_company_columns = ['storage_type', 'yandex_disk_folder_id', 'content_types', 'backup_provider', 'backup_remote_path']
    for col in new_company_columns:
        if col in company_columns:
            op.drop_column('companies', col)