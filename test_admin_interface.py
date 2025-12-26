#!/usr/bin/env python3
"""
Test admin interface functionality including:
1. Login page loading
2. Dashboard loading with metrics
3. Theme toggle functionality
4. Style rendering
"""

import asyncio
import sys
import os
import requests
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import get_db_session
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select

async def create_test_admin():
    """Create test admin user if not exists."""
    async with get_db_session() as db:
        # Check if admin exists
        result = await db.execute(
            select(User).where(User.email == "admin@vertexar.com")
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            # Create admin user
            admin = User(
                email="admin@vertexar.com",
                hashed_password=get_password_hash("admin123"),
                is_active=True,
                is_superuser=True
            )
            db.add(admin)
            await db.commit()
            print("✅ Created test admin user: admin@vertexar.com / admin123")
        else:
            print("✅ Admin user already exists")

def test_login_page():
    """Test if login page loads correctly."""
    print("\n🔍 Testing login page...")
    
    # Test basic login page access
    try:
        response = requests.get("http://localhost:8000/admin/login", timeout=10)
        if response.status_code == 200:
            print("✅ Login page loads successfully")
            
            # Check for key elements
            content = response.text
            if 'toggleTheme()' in content:
                print("✅ Theme toggle function found")
            else:
                print("❌ Theme toggle function missing")
                
            if 'bg-white dark:bg-gray-800' in content:
                print("✅ Dark mode styles found")
            else:
                print("❌ Dark mode styles missing")
                
            if 'tailwindcss.com' in content:
                print("✅ Tailwind CSS from CDN found")
            else:
                print("❌ Tailwind CSS not from CDN")
                
            if 'alpinejs' in content:
                print("✅ Alpine.js found")
            else:
                print("❌ Alpine.js missing")
        else:
            print(f"❌ Login page failed with status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to server: {e}")
        return False
    
    return True

def test_dashboard():
    """Test dashboard access (should redirect to login if not authenticated)."""
    print("\n🔍 Testing dashboard access...")
    
    try:
        response = requests.get("http://localhost:8000/admin", timeout=10, allow_redirects=False)
        if response.status_code == 302:
            print("✅ Dashboard correctly redirects to login when not authenticated")
        elif response.status_code == 200:
            print("✅ Dashboard loads (already authenticated)")
            
            # Check for metrics
            content = response.text
            if 'total_views' in content:
                print("✅ Total views metric found")
            else:
                print("❌ Total views metric missing")
                
            if 'unique_sessions' in content:
                print("✅ Unique sessions metric found")
            else:
                print("❌ Unique sessions metric missing")
        else:
            print(f"❌ Dashboard unexpected status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to server: {e}")
        return False
    
    return True

def test_static_files():
    """Test static file serving."""
    print("\n🔍 Testing static files...")
    
    try:
        response = requests.get("http://localhost:8000/static/css/tailwind.css", timeout=10)
        if response.status_code == 200:
            print("✅ Static CSS file accessible")
        else:
            print(f"❌ Static CSS file failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot access static files: {e}")

def main():
    """Run all tests."""
    print("🚀 Starting admin interface tests...")
    
    # Create test admin
    asyncio.run(create_test_admin())
    
    # Test various components
    test_login_page()
    test_dashboard()
    test_static_files()
    
    print("\n📝 Manual Testing Instructions:")
    print("1. Start the server: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
    print("2. Open browser: http://localhost:8000/admin/login")
    print("3. Login with: admin@vertexar.com / admin123")
    print("4. Test theme toggle (🌙/☀️ button)")
    print("5. Check dashboard metrics display correctly")
    print("6. Verify dark mode works on all pages")
    
    print("\n✨ Admin interface test completed!")

if __name__ == "__main__":
    main()