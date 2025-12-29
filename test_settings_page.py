#!/usr/bin/env python3
"""
Simple script to test the settings page functionality
without running the full FastAPI server.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.services.settings_service import SettingsService
from app.schemas.settings import AllSettings

async def test_settings_service():
    """Test the settings service functionality."""
    print("🔧 Testing Settings Service...")
    
    # Get configuration
    settings = get_settings()
    print(f"📊 Database URL: {settings.DATABASE_URL}")
    
    # Create database engine
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as db:
        try:
            # Initialize settings service
            settings_service = SettingsService(db)
            
            # Test getting all settings
            print("📋 Fetching all settings...")
            all_settings = await settings_service.get_all_settings()
            
            print("✅ Settings loaded successfully!")
            print(f"📝 General Settings:")
            print(f"   - Site Title: {all_settings.general.site_title}")
            print(f"   - Admin Email: {all_settings.general.admin_email}")
            print(f"   - Maintenance Mode: {all_settings.general.maintenance_mode}")
            
            print(f"🔒 Security Settings:")
            print(f"   - Password Min Length: {all_settings.security.password_min_length}")
            print(f"   - Session Timeout: {all_settings.security.session_timeout}")
            print(f"   - Require 2FA: {all_settings.security.require_2fa}")
            
            print(f"💾 Storage Settings:")
            print(f"   - Default Storage: {all_settings.storage.default_storage}")
            print(f"   - Max File Size: {all_settings.storage.max_file_size}MB")
            print(f"   - CDN Enabled: {all_settings.storage.cdn_enabled}")
            
            print(f"📧 Notification Settings:")
            print(f"   - Email Enabled: {all_settings.notifications.email_enabled}")
            print(f"   - Telegram Enabled: {all_settings.notifications.telegram_enabled}")
            
            print(f"🔌 API Settings:")
            print(f"   - API Keys Enabled: {all_settings.api.api_keys_enabled}")
            print(f"   - Documentation Public: {all_settings.api.documentation_public}")
            print(f"   - CORS Origins: {all_settings.api.cors_origins}")
            
            print(f"🔗 Integration Settings:")
            print(f"   - Google OAuth: {all_settings.integrations.google_oauth_enabled}")
            print(f"   - Payment Provider: {all_settings.integrations.payment_provider}")
            print(f"   - Analytics Enabled: {all_settings.integrations.analytics_enabled}")
            
            print(f"🎯 AR Settings:")
            print(f"   - MindAR Max Features: {all_settings.ar.mindar_max_features}")
            print(f"   - Marker Generation: {all_settings.ar.marker_generation_enabled}")
            print(f"   - Thumbnail Quality: {all_settings.ar.thumbnail_quality}%")
            
            # Test updating a setting
            print("\n🔄 Testing setting update...")
            await settings_service.set_setting(
                "site_title", 
                "Vertex AR B2B Platform - Test", 
                "string", 
                "general"
            )
            
            # Verify the update
            updated_settings = await settings_service.get_all_settings()
            if updated_settings.general.site_title == "Vertex AR B2B Platform - Test":
                print("✅ Setting update test passed!")
            else:
                print("❌ Setting update test failed!")
            
            # Restore original value
            await settings_service.set_setting(
                "site_title", 
                "Vertex AR B2B Platform", 
                "string", 
                "general"
            )
            
            return True
            
        except Exception as e:
            print(f"❌ Error testing settings service: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await engine.dispose()

def check_template_file():
    """Check if the settings template exists and has the expected structure."""
    print("\n📄 Checking Settings Template...")
    
    template_path = project_root / "templates" / "settings.html"
    
    if not template_path.exists():
        print(f"❌ Template file not found: {template_path}")
        return False
    
    print(f"✅ Template file found: {template_path}")
    
    # Read template and check for key elements
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
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
    
    missing_sections = []
    for section in required_sections:
        if section not in content:
            missing_sections.append(section)
    
    if missing_sections:
        print(f"❌ Missing template sections: {missing_sections}")
        return False
    
    print("✅ All required template sections found")
    
    # Check for form elements
    required_forms = [
        'action="/settings/general"',
        'action="/settings/security"',
        'action="/settings/storage"',
        'action="/settings/notifications"',
        'action="/settings/api"',
        'action="/settings/integrations"',
        'action="/settings/ar"'
    ]
    
    missing_forms = []
    for form in required_forms:
        if form not in content:
            missing_forms.append(form)
    
    if missing_forms:
        print(f"❌ Missing form actions: {missing_forms}")
        return False
    
    print("✅ All required form actions found")
    
    # Check for navigation
    if 'nav-link' not in content:
        print("❌ Navigation links not found")
        return False
    
    print("✅ Navigation links found")
    
    # Check for JavaScript functionality
    if 'DOMContentLoaded' not in content:
        print("❌ JavaScript functionality not found")
        return False
    
    print("✅ JavaScript functionality found")
    
    return True

def check_routes_file():
    """Check if the settings routes file exists and has the expected structure."""
    print("\n🛣️ Checking Settings Routes...")
    
    routes_path = project_root / "app" / "html" / "routes" / "settings.py"
    
    if not routes_path.exists():
        print(f"❌ Routes file not found: {routes_path}")
        return False
    
    print(f"✅ Routes file found: {routes_path}")
    
    # Read routes and check for key endpoints
    with open(routes_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for key endpoints
    required_endpoints = [
        '@router.get("/settings"',
        '@router.post("/settings/general"',
        '@router.post("/settings/security"',
        '@router.post("/settings/storage"',
        '@router.post("/settings/notifications"',
        '@router.post("/settings/api"',
        '@router.post("/settings/integrations"',
        '@router.post("/settings/ar"'
    ]
    
    missing_endpoints = []
    for endpoint in required_endpoints:
        if endpoint not in content:
            missing_endpoints.append(endpoint)
    
    if missing_endpoints:
        print(f"❌ Missing endpoints: {missing_endpoints}")
        return False
    
    print("✅ All required endpoints found")
    
    # Check for authentication
    if 'get_current_user_optional' not in content:
        print("❌ Authentication check not found")
        return False
    
    print("✅ Authentication checks found")
    
    # Check for error handling
    if 'try:' not in content or 'except' not in content:
        print("❌ Error handling not found")
        return False
    
    print("✅ Error handling found")
    
    return True

async def main():
    """Main test function."""
    print("🚀 Starting Settings Page Validation\n")
    
    # Check template file
    template_ok = check_template_file()
    
    # Check routes file  
    routes_ok = check_routes_file()
    
    # Test settings service
    service_ok = await test_settings_service()
    
    print("\n" + "="*50)
    print("📊 VALIDATION SUMMARY")
    print("="*50)
    print(f"Template File: {'✅ PASS' if template_ok else '❌ FAIL'}")
    print(f"Routes File:    {'✅ PASS' if routes_ok else '❌ FAIL'}")
    print(f"Settings Service: {'✅ PASS' if service_ok else '❌ FAIL'}")
    
    if all([template_ok, routes_ok, service_ok]):
        print("\n🎉 ALL TESTS PASSED! Settings page is ready for use.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)