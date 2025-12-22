"""initial schema

Revision ID: 28cd993514df
Revises: 
Create Date: 2025-12-17 02:06:25.157364

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28cd993514df'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('login_attempts', sa.Integer(), nullable=False),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # Create companies table
    op.create_table(
        'companies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_companies_id'), 'companies', ['id'], unique=False)

    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_company_id'), 'projects', ['company_id'], unique=False)
    op.create_index(op.f('ix_projects_id'), 'projects', ['id'], unique=False)
    op.create_index('ix_project_company_name', 'projects', ['company_id', 'name'], unique=False)

    # Create ar_content table
    op.create_table(
        'ar_content',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('active_video_id', sa.Integer(), nullable=True),
        sa.Column('unique_id', sa.UUID(), nullable=False),
        sa.Column('order_number', sa.String(length=50), nullable=False),
        sa.Column('customer_name', sa.String(length=255), nullable=True),
        sa.Column('customer_phone', sa.String(length=50), nullable=True),
        sa.Column('customer_email', sa.String(length=255), nullable=True),
        sa.Column('duration_years', sa.Integer(), nullable=False),
        sa.Column('views_count', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('content_metadata', sa.JSON(), nullable=True),
        sa.Column('photo_path', sa.String(length=500), nullable=True),
        sa.Column('photo_url', sa.String(length=500), nullable=True),
        sa.Column('video_path', sa.String(length=500), nullable=True),
        sa.Column('video_url', sa.String(length=500), nullable=True),
        sa.Column('qr_code_path', sa.String(length=500), nullable=True),
        sa.Column('qr_code_url', sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('unique_id')
    )
    op.create_index(op.f('ix_ar_content_company_id'), 'ar_content', ['company_id'], unique=False)
    op.create_index(op.f('ix_ar_content_id'), 'ar_content', ['id'], unique=False)
    op.create_index(op.f('ix_ar_content_project_id'), 'ar_content', ['project_id'], unique=False)
    op.create_index('ix_ar_content_project_order', 'ar_content', ['project_id', 'order_number'], unique=True)

    # Create videos table
    op.create_table(
        'videos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ar_content_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('video_path', sa.String(length=500), nullable=True),
        sa.Column('video_url', sa.String(length=500), nullable=True),
        sa.Column('thumbnail_path', sa.String(length=500), nullable=True),
        sa.Column('preview_url', sa.String(length=500), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('rotation_type', sa.String(length=20), nullable=False),
        sa.Column('rotation_order', sa.Integer(), nullable=False),
        sa.Column('subscription_end', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['ar_content_id'], ['ar_content.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_videos_ar_content_id'), 'videos', ['ar_content_id'], unique=False)
    op.create_index(op.f('ix_videos_id'), 'videos', ['id'], unique=False)

    # Create video_schedules table
    op.create_table(
        'video_schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.Integer(), nullable=False),
        sa.Column('schedule_type', sa.String(length=50), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('start_time', sa.String(length=8), nullable=True),
        sa.Column('end_time', sa.String(length=8), nullable=True),
        sa.Column('days_of_week', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_schedules_video_id'), 'video_schedules', ['video_id'], unique=False)

    # Create storage_connections table
    op.create_table(
        'storage_connections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('base_path', sa.String(length=500), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_tested_at', sa.DateTime(), nullable=True),
        sa.Column('test_status', sa.String(length=50), nullable=True),
        sa.Column('test_error', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create storage_folders table
    op.create_table(
        'storage_folders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('path', sa.String(length=500), nullable=False),
        sa.Column('folder_type', sa.String(length=50), nullable=True),
        sa.Column('files_count', sa.Integer(), nullable=False),
        sa.Column('total_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create folders table
    op.create_table(
        'folders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('path', sa.String(length=500), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['folders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create clients table
    op.create_table(
        'clients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('company_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create video_rotation_schedules table
    op.create_table(
        'video_rotation_schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ar_content_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('schedule_type', sa.String(length=50), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('start_time', sa.String(length=8), nullable=True),
        sa.Column('end_time', sa.String(length=8), nullable=True),
        sa.Column('days_of_week', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['ar_content_id'], ['ar_content.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create ar_view_sessions table
    op.create_table(
        'ar_view_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ar_content_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['ar_content_id'], ['ar_content.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ar_view_sessions_session_id'), 'ar_view_sessions', ['session_id'], unique=False)

    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False),
        sa.Column('recipient_id', sa.Integer(), nullable=True),
        sa.Column('sender_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create email_queue table
    op.create_table(
        'email_queue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recipient_email', sa.String(length=255), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('old_values', sa.JSON(), nullable=True),
        sa.Column('new_values', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)

    # Add check constraints
    op.create_check_constraint(
        'check_duration_years',
        'ar_content',
        'duration_years IN (1, 3, 5)'
    )
    op.create_check_constraint(
        'check_views_count_non_negative',
        'ar_content',
        'views_count >= 0'
    )


def downgrade() -> None:
    # Drop check constraints first
    op.drop_constraint('check_duration_years', 'ar_content', type_='check')
    op.drop_constraint('check_views_count_non_negative', 'ar_content', type_='check')

    # Drop tables in reverse order due to foreign key dependencies
    op.drop_table('audit_logs')
    op.drop_table('email_queue')
    op.drop_table('notifications')
    op.drop_table('ar_view_sessions')
    op.drop_table('video_rotation_schedules')
    op.drop_table('clients')
    op.drop_table('folders')
    op.drop_table('storage_folders')
    op.drop_table('storage_connections')
    op.drop_table('video_schedules')
    op.drop_table('videos')
    op.drop_table('ar_content')
    op.drop_table('projects')
    op.drop_table('companies')
    op.drop_table('users')