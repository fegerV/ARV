#!/usr/bin/env python3

import requests
import json

def test_login():
    """Test admin login functionality"""
    
    # Test the login page loads
    print("🔍 Testing login page accessibility...")
    try:
        response = requests.get("http://localhost:8000/admin/login")
        if response.status_code == 200:
            print("✅ Login page accessible")
        else:
            print(f"❌ Login page returned status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot access login page: {e}")
        return False
    
    # Test form-based login
    print("\n🔐 Testing form-based login...")
    login_data = {
        "username": "admin@vertexar.com",
        "password": "ChangeMe123!"
    }
    
    try:
        # Use session to preserve cookies
        session = requests.Session()
        response = session.post(
            "http://localhost:8000/api/auth/login-form",
            data=login_data,
            allow_redirects=False
        )
        
        if response.status_code in [302, 303]:
            # Login successful - redirect to admin
            print("✅ Login successful - redirect received")
            
            # Follow redirect to admin dashboard
            admin_response = session.get("http://localhost:8000/admin")
            if admin_response.status_code == 200:
                print("✅ Admin dashboard accessible after login")
                return True
            else:
                print(f"❌ Admin dashboard returned status: {admin_response.status_code}")
                return False
        else:
            print(f"❌ Login failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Login request failed: {e}")
        return False

def test_api_login():
    """Test API login endpoint"""
    print("\n🔧 Testing API login endpoint...")
    
    login_data = {
        "username": "admin@vertexar.com", 
        "password": "ChangeMe123!"
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/api/auth/login",
            data=login_data
        )
        
        if response.status_code == 200:
            result = response.json()
            if "access_token" in result:
                print("✅ API login successful - token received")
                return True
            else:
                print("❌ API login response missing token")
                return False
        else:
            print(f"❌ API login failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ API login request failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Vertex AR Admin Login")
    print("=" * 50)
    
    form_success = test_login()
    api_success = test_api_login()
    
    print("\n" + "=" * 50)
    if form_success and api_success:
        print("🎉 ALL TESTS PASSED! Admin login is working correctly.")
        print("\n📝 Login Credentials:")
        print("   Email: admin@vertexar.com")
        print("   Password: ChangeMe123!")
        print("   URL: http://localhost:8000/admin/login")
    else:
        print("❌ Some tests failed. Please check the issues above.")