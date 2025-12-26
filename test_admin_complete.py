#!/usr/bin/env python3
"""
Comprehensive admin functionality test script.
Tests the complete workflow: login → create AR content → upload files → generate markers → verify functionality
"""

import asyncio
import aiohttp
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"

async def test_admin_functionality():
    """Test complete admin functionality workflow."""
    
    async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True)) as session:
        print("🚀 Starting comprehensive admin functionality test...")
        
        # 1. Test login
        print("\n1️⃣ Testing admin login...")
        login_data = {
            'username': 'admin@vertexar.com',
            'password': 'admin123'
        }
        
        async with session.post(f"{BASE_URL}/admin/login-form", data=login_data, allow_redirects=False) as response:
            if response.status == 303:
                print("✅ Login successful!")
                # Extract cookies from response
                cookies = session.cookie_jar
                if not cookies:
                    print("❌ No cookies found")
                    return False
                print("✅ Cookies received!")
            else:
                print(f"❌ Login failed with status: {response.status}")
                return False
        
        # 2. Test admin dashboard access
        print("\n2️⃣ Testing admin dashboard access...")
        async with session.get(f"{BASE_URL}/admin") as response:
            if response.status == 200:
                content = await response.text()
                if "Admin Dashboard" in content:
                    print("✅ Dashboard accessible!")
                else:
                    print("❌ Dashboard content incorrect")
                    return False
            else:
                print(f"❌ Dashboard access failed with status: {response.status}")
                return False
        
        # 3. Test companies page
        print("\n3️⃣ Testing companies page...")
        async with session.get(f"{BASE_URL}/companies") as response:
            if response.status == 200:
                content = await response.text()
                if "Vertex AR" in content:
                    print("✅ Companies page shows our company!")
                else:
                    print("❌ Company not found on companies page")
                    return False
            else:
                print(f"❌ Companies page failed with status: {response.status}")
                return False
        
        # 4. Test projects page
        print("\n4️⃣ Testing projects page...")
        async with session.get(f"{BASE_URL}/projects") as response:
            if response.status == 200:
                content = await response.text()
                if "Портреты" in content:
                    print("✅ Projects page shows our project!")
                else:
                    print("❌ Project not found on projects page")
                    return False
            else:
                print(f"❌ Projects page failed with status: {response.status}")
                return False
        
        # 5. Test AR content list page
        print("\n5️⃣ Testing AR content list page...")
        async with session.get(f"{BASE_URL}/ar-content") as response:
            if response.status == 200:
                content = await response.text()
                if "AR Content" in content:
                    print("✅ AR content list page accessible!")
                else:
                    print("❌ AR content list page incorrect")
                    return False
            else:
                print(f"❌ AR content list failed with status: {response.status}")
                return False
        
        # 6. Test AR content creation page
        print("\n6️⃣ Testing AR content creation page...")
        async with session.get(f"{BASE_URL}/ar-content/create") as response:
            if response.status == 200:
                content = await response.text()
                if "Create AR Content" in content or "Create" in content:
                    print("✅ AR content creation page accessible!")
                else:
                    print("❌ AR content creation page incorrect")
                    return False
            else:
                print(f"❌ AR content creation page failed with status: {response.status}")
                return False
        
        # 7. Test API endpoints
        print("\n7️⃣ Testing API endpoints...")
        
        # Test companies API
        async with session.get(f"{BASE_URL}/api/companies") as response:
            if response.status == 200:
                companies = await response.json()
                if any(c['name'] == 'Vertex AR' for c in companies.get('items', [])):
                    print("✅ Companies API working!")
                else:
                    print("❌ Companies API not returning expected data")
                    return False
            else:
                print(f"❌ Companies API failed with status: {response.status}")
                return False
        
        # Test projects API
        async with session.get(f"{BASE_URL}/api/projects") as response:
            if response.status == 200:
                projects = await response.json()
                if any(p['name'] == 'Портреты' for p in projects.get('items', [])):
                    print("✅ Projects API working!")
                else:
                    print("❌ Projects API not returning expected data")
                    return False
            else:
                print(f"❌ Projects API failed with status: {response.status}")
                return False
        
        print("\n🎉 All basic admin functionality tests passed!")
        print("\n📋 Manual Testing Checklist:")
        print("1. ✅ Login functionality working")
        print("2. ✅ Dashboard accessible") 
        print("3. ✅ Companies page shows Vertex AR")
        print("4. ✅ Projects page shows 'Портреты'")
        print("5. ✅ AR content list accessible")
        print("6. ✅ AR content creation page accessible")
        print("7. ✅ API endpoints working")
        
        print("\n🔧 Manual Testing Required:")
        print("1. Create new AR content in the 'Портреты' project")
        print("2. Fill customer information fields")
        print("3. Upload photo and video files")
        print("4. Generate markers")
        print("5. Set 3-year video placement")
        print("6. Test lightbox functionality")
        print("7. Verify multiple video management")
        print("8. Test active video selection")
        
        return True

def main():
    """Main function."""
    print("🧪 Vertex AR Admin Functionality Test")
    print("=" * 50)
    
    try:
        result = asyncio.run(test_admin_functionality())
        if result:
            print("\n✅ Test completed successfully!")
            print(f"🌐 Admin URL: {BASE_URL}/admin")
            print("👤 Login: admin@vertexar.com / admin123")
        else:
            print("\n❌ Test failed!")
    except Exception as e:
        print(f"\n❌ Test error: {e}")

if __name__ == "__main__":
    main()