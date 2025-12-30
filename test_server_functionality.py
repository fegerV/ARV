#!/usr/bin/env python3
"""
Test server functionality for AR Content form
"""

import asyncio
import aiohttp
import json
from pathlib import Path

async def test_server_endpoints():
    """Test that server endpoints are working correctly"""
    print("🚀 Testing Server Functionality\n")
    
    base_url = "http://localhost:8000"
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test main AR content list page
            print("🔍 Testing AR content list page...")
            async with session.get(f"{base_url}/ar-content") as resp:
                if resp.status == 200:
                    print("✅ AR content list page loads successfully")
                elif resp.status == 401:
                    print("✅ AR content list page correctly requires authentication")
                else:
                    print(f"❌ AR content list page returned status {resp.status}")
            
            # Test create page (should redirect to login if not authenticated)
            print("\n🔍 Testing AR content create page...")
            async with session.get(f"{base_url}/ar-content/create") as resp:
                if resp.status == 200:
                    print("✅ AR content create page loads successfully")
                elif resp.status == 401:
                    print("✅ AR content create page correctly requires authentication")
                else:
                    print(f"❌ AR content create page returned status {resp.status}")
            
            # Test admin login page
            print("\n🔍 Testing admin login page...")
            async with session.get(f"{base_url}/admin/login") as resp:
                if resp.status == 200:
                    print("✅ Admin login page loads successfully")
                    content = await resp.text()
                    
                    # Check for form elements
                    if 'email' in content and 'password' in content:
                        print("✅ Login form contains required fields")
                    else:
                        print("❌ Login form missing required fields")
                else:
                    print(f"❌ Admin login page returned status {resp.status}")
                    
    except aiohttp.ClientConnectorError:
        print("⚠️  Server is not running. Please start the server with:")
        print("   source venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
        return False
    except Exception as e:
        print(f"❌ Error testing server: {e}")
        return False
    
    return True

def test_static_files():
    """Test that static files are accessible"""
    print("\n🔍 Testing static files...")
    
    static_files = [
        "/static/css/tailwind.css",
    ]
    
    base_url = "http://localhost:8000"
    
    # We can't test without server running, so just check if files exist
    for file_path in static_files:
        full_path = Path(f"/home/engine/project{file_path}")
        if full_path.exists():
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
    
    return True

async def main():
    """Run all server tests"""
    print("🚀 AR Content Form Server Tests\n")
    
    # Test static files first
    test_static_files()
    
    # Test server endpoints
    await test_server_endpoints()
    
    print("\n📝 Manual Testing Instructions:")
    print("1. Start the server: source venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
    print("2. Open browser to: http://localhost:8000/admin/login")
    print("3. Login with: admin@vertexar.com / admin123")
    print("4. Navigate to: http://localhost:8000/ar-content/create")
    print("5. Test the following:")
    print("   - Company dropdown shows companies")
    print("   - Selecting a company shows related projects")
    print("   - Form elements are visible in dark mode")
    print("   - Submit button appears when all fields are filled")
    print("   - Files can be uploaded for photo and video")

if __name__ == "__main__":
    asyncio.run(main())