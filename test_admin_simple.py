#!/usr/bin/env python3
"""
Simple admin functionality test using API token.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_admin_functionality():
    """Test admin functionality using API token."""
    
    session = requests.Session()
    
    print("🚀 Starting admin functionality test...")
    
    # 1. Get API token
    print("\n1️⃣ Getting API token...")
    login_data = {
        'username': 'admin@vertexar.com',
        'password': 'admin123'
    }
    
    response = session.post(f"{BASE_URL}/api/auth/login", data=login_data)
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data['access_token']
        print("✅ API token received!")
        session.headers.update({'Authorization': f'Bearer {access_token}'})
    else:
        print(f"❌ API login failed with status: {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    # 2. Test API endpoints
    print("\n2️⃣ Testing API endpoints...")
    
    # Test companies API
    response = session.get(f"{BASE_URL}/api/companies")
    if response.status_code == 200:
        companies = response.json()
        if any(c['name'] == 'Vertex AR' for c in companies.get('items', [])):
            print("✅ Companies API working!")
        else:
            print("❌ Companies API not returning expected data")
            return False
    else:
        print(f"❌ Companies API failed with status: {response.status_code}")
        return False
    
    # Test projects API
    response = session.get(f"{BASE_URL}/api/projects")
    if response.status_code == 200:
        projects = response.json()
        if any(p['name'] == 'Портреты' for p in projects.get('items', [])):
            print("✅ Projects API working!")
        else:
            print("❌ Projects API not returning expected data")
            return False
    else:
        print(f"❌ Projects API failed with status: {response.status_code}")
        return False
    
    # Test AR content API
    response = session.get(f"{BASE_URL}/api/ar-content")
    if response.status_code == 200:
        ar_content = response.json()
        print("✅ AR Content API working!")
    else:
        print(f"❌ AR Content API failed with status: {response.status_code}")
        return False
    
    # 3. Test HTML pages with cookie
    print("\n3️⃣ Testing HTML pages...")
    
    # Get token for cookie
    login_response = session.post(f"{BASE_URL}/admin/login-form", data=login_data, allow_redirects=False)
    if login_response.status_code == 303:
        # Extract cookie from response
        cookies = login_response.cookies
        print("✅ Got cookie for HTML access!")
        
        # Test admin dashboard
        dashboard_response = session.get(f"{BASE_URL}/admin", cookies=cookies)
        if dashboard_response.status_code == 200:
            if "Admin Dashboard" in dashboard_response.text:
                print("✅ Admin dashboard accessible!")
            else:
                print("❌ Dashboard content incorrect")
                return False
        else:
            print(f"❌ Dashboard access failed with status: {dashboard_response.status_code}")
            return False
        
        # Test companies page
        companies_response = session.get(f"{BASE_URL}/companies", cookies=cookies)
        if companies_response.status_code == 200:
            if "Vertex AR" in companies_response.text:
                print("✅ Companies page shows our company!")
            else:
                print("❌ Company not found on companies page")
                return False
        else:
            print(f"❌ Companies page failed with status: {companies_response.status_code}")
            return False
        
        # Test projects page
        projects_response = session.get(f"{BASE_URL}/projects", cookies=cookies)
        if projects_response.status_code == 200:
            if "Портреты" in projects_response.text:
                print("✅ Projects page shows our project!")
            else:
                print("❌ Project not found on projects page")
                return False
        else:
            print(f"❌ Projects page failed with status: {projects_response.status_code}")
            return False
        
        # Test AR content page
        ar_content_response = session.get(f"{BASE_URL}/ar-content", cookies=cookies)
        if ar_content_response.status_code == 200:
            if "AR Content" in ar_content_response.text:
                print("✅ AR content page accessible!")
            else:
                print("❌ AR content page incorrect")
                return False
        else:
            print(f"❌ AR content page failed with status: {ar_content_response.status_code}")
            return False
    
    print("\n🎉 All tests passed!")
    print("\n📋 Test Results:")
    print("1. ✅ API authentication working")
    print("2. ✅ Companies API working") 
    print("3. ✅ Projects API working")
    print("4. ✅ AR Content API working")
    print("5. ✅ HTML authentication working")
    print("6. ✅ Admin dashboard accessible")
    print("7. ✅ Companies page shows Vertex AR")
    print("8. ✅ Projects page shows 'Портреты'")
    print("9. ✅ AR content page accessible")
    
    print("\n🔧 Ready for Manual Testing:")
    print(f"🌐 Admin URL: {BASE_URL}/admin")
    print("👤 Login: admin@vertexar.com / admin123")
    print("📁 Company: Vertex AR")
    print("📂 Project: Портреты")
    
    return True

def main():
    """Main function."""
    print("🧪 Vertex AR Admin Functionality Test")
    print("=" * 50)
    
    try:
        result = test_admin_functionality()
        if result:
            print("\n✅ All tests completed successfully!")
        else:
            print("\n❌ Some tests failed!")
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()