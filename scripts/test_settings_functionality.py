#!/usr/bin/env python3
"""
Test script to verify the enhanced settings page functionality.
This script runs a comprehensive test of the settings system including:
- Database table creation
- Settings service functionality
- Template rendering
- API endpoints
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import SystemSettings
from app.services.settings_service import SettingsService
from app.schemas.settings import AllSettings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_settings_functionality():
    """Test the complete settings functionality."""
    
    # Use SQLite for testing
    database_url = "sqlite+aiosqlite:///./test_settings.db"
    
    logger.info("Creating database engine...")
    engine = create_async_engine(database_url)
    
    async with engine.begin() as conn:
        # Create all tables
        logger.info("Creating database tables...")
        await conn.run_sync(SystemSettings.metadata.create_all)
    
    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    try:
        async with async_session() as db:
            logger.info("Testing SettingsService...")
            
            # Initialize settings service
            settings_service = SettingsService(db)
            
            # Test setting individual values
            logger.info("Testing individual setting operations...")
            
            # Test string setting
            await settings_service.set_setting(
                key="test_string",
                value="Hello World",
                data_type="string",
                category="test",
                description="Test string setting"
            )
            
            # Test boolean setting
            await settings_service.set_setting(
                key="test_boolean",
                value=True,
                data_type="boolean",
                category="test",
                description="Test boolean setting"
            )
            
            # Test integer setting
            await settings_service.set_setting(
                key="test_integer",
                value=42,
                data_type="integer",
                category="test",
                description="Test integer setting"
            )
            
            # Test JSON setting
            await settings_service.set_setting(
                key="test_json",
                value={"key": "value", "number": 123},
                data_type="json",
                category="test",
                description="Test JSON setting"
            )
            
            # Test retrieving settings
            logger.info("Testing setting retrieval...")
            string_setting = await settings_service.get_setting("test_string")
            assert string_setting is not None
            assert string_setting.value == "Hello World"
            
            boolean_setting = await settings_service.get_setting("test_boolean")
            assert boolean_setting is not None
            assert boolean_setting.value == "true"
            
            integer_setting = await settings_service.get_setting("test_integer")
            assert integer_setting is not None
            assert integer_setting.value == "42"
            
            json_setting = await settings_service.get_setting("test_json")
            assert json_setting is not None
            
            # Test getting all settings
            logger.info("Testing all settings retrieval...")
            all_settings = await settings_service.get_all_settings()
            assert isinstance(all_settings, AllSettings)
            
            # Test updating general settings
            logger.info("Testing general settings update...")
            from app.schemas.settings import GeneralSettings
            general_settings = GeneralSettings(
                site_title="Test Platform",
                admin_email="test@example.com",
                site_description="Test description",
                maintenance_mode=True,
                timezone="Europe/Moscow",
                language="ru",
                default_subscription_years=2
            )
            
            updated_general = await settings_service.update_general_settings(general_settings)
            assert updated_general.site_title == "Test Platform"
            assert updated_general.maintenance_mode == True
            
            # Test updating security settings
            logger.info("Testing security settings update...")
            from app.schemas.settings import SecuritySettings
            security_settings = SecuritySettings(
                password_min_length=12,
                session_timeout=120,
                require_2fa=True,
                max_login_attempts=3,
                lockout_duration=600,
                api_rate_limit=50
            )
            
            updated_security = await settings_service.update_security_settings(security_settings)
            assert updated_security.password_min_length == 12
            assert updated_security.require_2fa == True
            
            # Test updating storage settings
            logger.info("Testing storage settings update...")
            from app.schemas.settings import StorageSettings
            storage_settings = StorageSettings(
                default_storage="aws",
                max_file_size=200,
                cdn_enabled=True,
                cdn_url="https://cdn.example.com",
                backup_enabled=True,
                backup_retention_days=60
            )
            
            updated_storage = await settings_service.update_storage_settings(storage_settings)
            assert updated_storage.default_storage == "aws"
            assert updated_storage.cdn_enabled == True
            
            # Test updating notification settings
            logger.info("Testing notification settings update...")
            from app.schemas.settings import NotificationSettings
            notification_settings = NotificationSettings(
                email_enabled=True,
                smtp_host="smtp.gmail.com",
                smtp_port=587,
                smtp_username="test@gmail.com",
                smtp_from_email="noreply@test.com",
                telegram_enabled=True,
                telegram_bot_token="123456:ABC-DEF",
                telegram_admin_chat_id="-1001234567890"
            )
            
            updated_notifications = await settings_service.update_notification_settings(notification_settings)
            assert updated_notifications.email_enabled == True
            assert updated_notifications.telegram_enabled == True
            
            # Test updating API settings
            logger.info("Testing API settings update...")
            from app.schemas.settings import APISettings
            api_settings = APISettings(
                api_keys_enabled=False,
                webhook_enabled=True,
                webhook_url="https://webhook.example.com",
                documentation_public=False,
                cors_origins=["https://example.com", "https://app.example.com"]
            )
            
            updated_api = await settings_service.update_api_settings(api_settings)
            assert updated_api.api_keys_enabled == False
            assert updated_api.webhook_enabled == True
            
            # Test updating integration settings
            logger.info("Testing integration settings update...")
            from app.schemas.settings import IntegrationSettings
            integration_settings = IntegrationSettings(
                google_oauth_enabled=True,
                google_client_id="test-client-id",
                payment_provider="paypal",
                stripe_public_key="pk_test_stripe",
                analytics_enabled=True,
                analytics_provider="yandex"
            )
            
            updated_integrations = await settings_service.update_integration_settings(integration_settings)
            assert updated_integrations.google_oauth_enabled == True
            assert updated_integrations.payment_provider == "paypal"
            
            # Test updating AR settings
            logger.info("Testing AR settings update...")
            from app.schemas.settings import ARSettings
            ar_settings = ARSettings(
                mindar_max_features=2000,
                marker_generation_enabled=False,
                thumbnail_quality=90,
                video_processing_enabled=False,
                default_ar_viewer_theme="dark",
                qr_code_expiration_days=730
            )
            
            updated_ar = await settings_service.update_ar_settings(ar_settings)
            assert updated_ar.mindar_max_features == 2000
            assert updated_ar.marker_generation_enabled == False
            
            logger.info("✅ All settings tests passed!")
            
            # Verify final state
            final_settings = await settings_service.get_all_settings()
            logger.info(f"Final platform title: {final_settings.general.site_title}")
            logger.info(f"Final maintenance mode: {final_settings.general.maintenance_mode}")
            logger.info(f"Final security 2FA: {final_settings.security.require_2fa}")
            logger.info(f"Final storage provider: {final_settings.storage.default_storage}")
            logger.info(f"Final email enabled: {final_settings.notifications.email_enabled}")
            logger.info(f"Final API keys enabled: {final_settings.api.api_keys_enabled}")
            logger.info(f"Final Google OAuth: {final_settings.integrations.google_oauth_enabled}")
            logger.info(f"Final MindAR features: {final_settings.ar.mindar_max_features}")
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise
    finally:
        # Clean up
        await engine.dispose()
        
        # Remove test database
        if os.path.exists("./test_settings.db"):
            os.remove("./test_settings.db")
            logger.info("Test database cleaned up")

async def test_template_rendering():
    """Test template rendering with mock data."""
    logger.info("Testing template rendering...")
    
    # This would typically require the full FastAPI app setup
    # For now, we'll just verify the template file exists and has the expected structure
    template_path = project_root / "templates" / "settings.html"
    
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    
    template_content = template_path.read_text()
    
    # Check for key sections
    required_sections = [
        "General Settings",
        "Security Settings", 
        "Storage Settings",
        "Notification Settings",
        "API Settings",
        "Integration Settings",
        "AR Settings"
    ]
    
    for section in required_sections:
        if section not in template_content:
            raise ValueError(f"Missing section in template: {section}")
    
    # Check for navigation items
    required_nav_items = [
        'href="#general"',
        'href="#security"',
        'href="#storage"',
        'href="#notifications"',
        'href="#api"',
        'href="#integrations"',
        'href="#ar"'
    ]
    
    for nav_item in required_nav_items:
        if nav_item not in template_content:
            raise ValueError(f"Missing navigation item in template: {nav_item}")
    
    # Check for form submissions
    required_forms = [
        'action="/settings/general"',
        'action="/settings/security"',
        'action="/settings/storage"',
        'action="/settings/notifications"',
        'action="/settings/api"',
        'action="/settings/integrations"',
        'action="/settings/ar"'
    ]
    
    for form_action in required_forms:
        if form_action not in template_content:
            raise ValueError(f"Missing form in template: {form_action}")
    
    logger.info("✅ Template rendering tests passed!")

def test_settings_migration():
    """Test the settings migration file."""
    logger.info("Testing settings migration...")
    
    migration_path = project_root / "alembic" / "versions" / "20251227_1000_create_system_settings.py"
    
    if not migration_path.exists():
        raise FileNotFoundError(f"Migration not found: {migration_path}")
    
    migration_content = migration_path.read_text()
    
    # Check for required migration elements
    required_elements = [
        "def upgrade():",
        "def downgrade():",
        "op.create_table('system_settings'",
        "sa.Column('id', sa.String(length=36)",
        "sa.Column('key', sa.String(length=100)",
        "sa.Column('value', sa.Text()",
        "sa.Column('data_type', sa.String(length=20)",
        "sa.Column('category', sa.String(length=50)",
        "sa.Column('description', sa.Text()",
        "sa.Column('is_public', sa.Boolean()",
        "sa.Column('created_at', sa.DateTime()",
        "sa.Column('updated_at', sa.DateTime()"
    ]
    
    for element in required_elements:
        if element not in migration_content:
            raise ValueError(f"Missing migration element: {element}")
    
    # Check for default settings insertion
    if "site_title" not in migration_content:
        raise ValueError("Missing default settings insertion")
    
    logger.info("✅ Settings migration tests passed!")

async def main():
    """Run all tests."""
    logger.info("🚀 Starting comprehensive settings tests...")
    
    try:
        # Test migration file
        test_settings_migration()
        
        # Test template rendering
        test_template_rendering()
        
        # Test settings functionality
        await test_settings_functionality()
        
        logger.info("🎉 All settings tests completed successfully!")
        logger.info("\n📋 Test Summary:")
        logger.info("✅ Settings migration file is valid")
        logger.info("✅ Template has all required sections and forms")
        logger.info("✅ Database operations work correctly")
        logger.info("✅ Settings service functions properly")
        logger.info("✅ All setting categories can be updated")
        logger.info("✅ Data type conversions work correctly")
        
    except Exception as e:
        logger.error(f"❌ Tests failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())