"""Create system_settings table

Revision ID: 20251227_1000_create_system_settings
Revises: 20251223_1200_comprehensive_ar_content_fix
Create Date: 2025-12-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251227_1000_create_system_settings'
down_revision = 'update_notifications_2024'
branch_labels = None
depends_on = None


def upgrade():
    """Create system_settings table."""
    # Create system_settings table
    op.create_table(
        'system_settings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('data_type', sa.String(length=20), nullable=True, default='string'),
        sa.Column('category', sa.String(length=50), nullable=True, default='general'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_system_settings_key'), 'system_settings', ['key'], unique=True)
    op.create_index(op.f('ix_system_settings_category'), 'system_settings', ['category'])
    
    # Insert default settings
    default_settings = [
        # General Settings
        ('site_title', 'Vertex AR B2B Platform', 'string', 'general', 'Platform name shown in header', True),
        ('admin_email', 'admin@vertexar.com', 'string', 'general', 'Platform administrator email', True),
        ('site_description', 'B2B SaaS platform for creating AR content based on image recognition (NFT markers)', 'string', 'general', 'Platform description for SEO and meta tags', True),
        ('maintenance_mode', 'false', 'boolean', 'general', 'Temporarily disable public access to platform', False),
        ('timezone', 'UTC', 'string', 'general', 'Default timezone for platform', False),
        ('language', 'en', 'string', 'general', 'Default language for platform', False),
        ('default_subscription_years', '1', 'integer', 'general', 'Default subscription duration in years', False),
        
        # Security Settings
        ('password_min_length', '8', 'integer', 'security', 'Minimum password length for user accounts', False),
        ('session_timeout', '60', 'integer', 'security', 'Session timeout in minutes', False),
        ('require_2fa', 'false', 'boolean', 'security', 'Require two-factor authentication for all users', False),
        ('max_login_attempts', '5', 'integer', 'security', 'Maximum number of login attempts before lockout', False),
        ('lockout_duration', '300', 'integer', 'security', 'Lockout duration in seconds after failed attempts', False),
        ('api_rate_limit', '100', 'integer', 'security', 'API rate limit per minute', False),
        
        # Storage Settings
        ('default_storage', 'local', 'string', 'storage', 'Default storage provider for files', False),
        ('max_file_size', '100', 'integer', 'storage', 'Maximum file size in MB', False),
        ('cdn_enabled', 'false', 'boolean', 'storage', 'Enable CDN for static files', False),
        ('cdn_url', '', 'string', 'storage', 'Custom CDN URL for static files', False),
        ('backup_enabled', 'true', 'boolean', 'storage', 'Enable automatic data backups', False),
        ('backup_retention_days', '30', 'integer', 'storage', 'Number of days to retain backups', False),
        
        # Notification Settings
        ('email_enabled', 'true', 'boolean', 'notifications', 'Enable email notifications', False),
        ('smtp_host', '', 'string', 'notifications', 'SMTP server host', False),
        ('smtp_port', '587', 'integer', 'notifications', 'SMTP server port', False),
        ('smtp_username', '', 'string', 'notifications', 'SMTP username', False),
        ('smtp_from_email', 'noreply@vertexar.com', 'string', 'notifications', 'From email address for notifications', False),
        ('telegram_enabled', 'false', 'boolean', 'notifications', 'Enable Telegram notifications', False),
        ('telegram_bot_token', '', 'string', 'notifications', 'Telegram bot token', False),
        ('telegram_admin_chat_id', '', 'string', 'notifications', 'Telegram admin chat ID', False),
        
        # API Settings
        ('api_keys_enabled', 'true', 'boolean', 'api', 'Enable API key authentication', False),
        ('webhook_enabled', 'false', 'boolean', 'api', 'Enable webhook notifications', False),
        ('webhook_url', '', 'string', 'api', 'Webhook URL for event notifications', False),
        ('documentation_public', 'true', 'boolean', 'api', 'Make API documentation public', False),
        ('cors_origins', '["http://localhost:3000", "http://localhost:8000"]', 'json', 'api', 'CORS allowed origins', False),
        
        # Integration Settings
        ('google_oauth_enabled', 'false', 'boolean', 'integrations', 'Enable Google OAuth authentication', False),
        ('google_client_id', '', 'string', 'integrations', 'Google OAuth client ID', False),
        ('payment_provider', 'stripe', 'string', 'integrations', 'Default payment provider', False),
        ('stripe_public_key', '', 'string', 'integrations', 'Stripe public key', False),
        ('analytics_enabled', 'false', 'boolean', 'integrations', 'Enable analytics tracking', False),
        ('analytics_provider', 'google', 'string', 'integrations', 'Analytics provider', False),
        
        # AR Settings
        ('mindar_max_features', '1000', 'integer', 'ar', 'Maximum feature points for MindAR marker detection', False),
        ('marker_generation_enabled', 'true', 'boolean', 'ar', 'Enable automatic MindAR marker generation', False),
        ('thumbnail_quality', '80', 'integer', 'ar', 'JPEG quality for generated thumbnails', False),
        ('video_processing_enabled', 'true', 'boolean', 'ar', 'Enable background video processing', False),
        ('default_ar_viewer_theme', 'default', 'string', 'ar', 'Default AR viewer theme', False),
        ('qr_code_expiration_days', '365', 'integer', 'ar', 'Default QR code expiration in days', False),
    ]
    
    # Insert default settings
    for setting in default_settings:
        op.execute(
            sa.text("""
                INSERT INTO system_settings (id, key, value, data_type, category, description, is_public, created_at, updated_at)
                VALUES (gen_random_uuid(), :key, :value, :data_type, :category, :description, :is_public, NOW(), NOW())
                ON CONFLICT (key) DO NOTHING
            """),
            {
                'key': setting[0],
                'value': setting[1],
                'data_type': setting[2],
                'category': setting[3],
                'description': setting[4],
                'is_public': setting[5]
            }
        )


def downgrade():
    """Drop system_settings table."""
    op.drop_index(op.f('ix_system_settings_category'), table_name='system_settings')
    op.drop_index(op.f('ix_system_settings_key'), table_name='system_settings')
    op.drop_table('system_settings')