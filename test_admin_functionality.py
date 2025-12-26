#!/usr/bin/env python3
"""
Test script to verify admin functionality without running full server
"""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_admin_functionality():
    """Test admin functionality"""
    print("🔍 Testing Admin Functionality")
    print("=" * 50)
    
    # Test 1: Check template files exist and have proper content
    print("\n1. 📄 Checking Template Files...")
    
    required_templates = [
        "templates/base.html",
        "templates/base_auth.html", 
        "templates/admin/login.html",
        "templates/dashboard/index.html",
        "templates/components/header.html",
        "templates/components/sidebar.html"
    ]
    
    for template in required_templates:
        if os.path.exists(template):
            print(f"   ✅ {template}")
        else:
            print(f"   ❌ {template} - MISSING")
    
    # Test 2: Check CSS classes are correct
    print("\n2. 🎨 Checking CSS Classes...")
    
    css_issues = []
    for template in required_templates:
        if os.path.exists(template):
            with open(template, 'r') as f:
                content = f.read()
                # Check for common CSS class typos
                if 'bg-indigo-60' in content:
                    css_issues.append(f"{template}: bg-indigo-60 found")
                if 'text-gray-30' in content:
                    css_issues.append(f"{template}: text-gray-30 found")
                if 'dark:text-gray-30' in content:
                    css_issues.append(f"{template}: dark:text-gray-30 found")
    
    if css_issues:
        for issue in css_issues:
            print(f"   ❌ {issue}")
    else:
        print("   ✅ No CSS class typos found")
    
    # Test 3: Check for dark mode functionality
    print("\n3. 🌙 Checking Dark Mode Support...")
    
    dark_mode_features = {
        "Alpine.js dark mode function": False,
        "Theme toggle button": False,
        "Dark mode CSS classes": False
    }
    
    # Check base.html for dark mode function
    if os.path.exists("templates/base.html"):
        with open("templates/base.html", 'r') as f:
            content = f.read()
            if "darkMode()" in content and "localStorage.getItem('darkMode')" in content:
                dark_mode_features["Alpine.js dark mode function"] = True
    
    # Check login template for theme toggle
    if os.path.exists("templates/admin/login.html"):
        with open("templates/admin/login.html", 'r') as f:
            content = f.read()
            if "@click=\"darkMode.toggle()\"" in content:
                dark_mode_features["Theme toggle button"] = True
    
    # Check for dark mode CSS classes
    for template in required_templates:
        if os.path.exists(template):
            with open(template, 'r') as f:
                content = f.read()
                if "dark:" in content:
                    dark_mode_features["Dark mode CSS classes"] = True
                    break
    
    for feature, status in dark_mode_features.items():
        if status:
            print(f"   ✅ {feature}")
        else:
            print(f"   ❌ {feature}")
    
    # Test 4: Check migration files
    print("\n4. 🗄️ Checking Migration Files...")
    
    migration_files = [
        "alembic/versions/20251223_1200_comprehensive_ar_content_fix.py",
        "alembic/versions/20241226_1200_update_notifications_table.py",
        "alembic/versions/20251227_1000_create_system_settings.py"
    ]
    
    migration_issues = []
    for migration in migration_files:
        if os.path.exists(migration):
            with open(migration, 'r') as f:
                content = f.read()
                # Check for PostgreSQL-specific functions that should be SQLite compatible
                if "gen_random_uuid()" in content:
                    migration_issues.append(f"{migration}: Contains gen_random_uuid() - not SQLite compatible")
                # Check for proper revision chain
                if "down_revision = 'update_notifications_2024'" in content and "20251227" in migration:
                    migration_issues.append(f"{migration}: Wrong down_revision")
        else:
            migration_issues.append(f"{migration} - MISSING")
    
    if migration_issues:
        for issue in migration_issues:
            print(f"   ❌ {issue}")
    else:
        print("   ✅ All migration files are correct")
    
    # Test 5: Check analytics API structure
    print("\n5. 📊 Checking Analytics API...")
    
    if os.path.exists("app/api/routes/analytics.py"):
        with open("app/api/routes/analytics.py", 'r') as f:
            content = f.read()
            
            analytics_features = {
                "Returns total_views": "total_views" in content,
                "Returns unique_sessions": "unique_sessions" in content,
                "Returns active_content": "active_content" in content,
                "Returns active_companies": "active_companies" in content,
                "Returns active_projects": "active_projects" in content,
                "Returns revenue": "revenue" in content,
                "Returns uptime": "uptime" in content
            }
            
            for feature, status in analytics_features.items():
                if status:
                    print(f"   ✅ {feature}")
                else:
                    print(f"   ❌ {feature}")
    else:
        print("   ❌ Analytics API file missing")
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 SUMMARY")
    print("=" * 50)
    
    total_checks = 5
    passed_checks = sum([
        all(os.path.exists(t) for t in required_templates),
        len(css_issues) == 0,
        all(dark_mode_features.values()),
        len(migration_issues) == 0,
        os.path.exists("app/api/routes/analytics.py")
    ])
    
    print(f"✅ Passed: {passed_checks}/{total_checks}")
    print(f"❌ Failed: {total_checks - passed_checks}/{total_checks}")
    
    if passed_checks == total_checks:
        print("\n🎉 All tests passed! Admin functionality looks good.")
        return True
    else:
        print("\n⚠️ Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_admin_functionality())
    sys.exit(0 if success else 1)