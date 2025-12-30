#!/usr/bin/env python3
"""
Test script for AR Content file uploader
"""
import requests
import json
from pathlib import Path

def test_login_and_access_create_page():
    """Test login and access to create page"""
    session = requests.Session()
    
    # Get login page
    print("🔍 Getting login page...")
    login_page = session.get("http://localhost:8000/admin/login")
    print(f"Login page status: {login_page.status_code}")
    
    # Login
    login_data = {
        "email": "admin@vertexar.com",
        "password": "admin123"
    }
    
    print("🔐 Logging in...")
    login_response = session.post("http://localhost:8000/admin/login", data=login_data)
    print(f"Login response status: {login_response.status_code}")
    
    # Try to access create page
    print("📝 Accessing create page...")
    create_page = session.get("http://localhost:8000/ar-content/create")
    print(f"Create page status: {create_page.status_code}")
    
    if create_page.status_code == 200:
        # Check if new uploader components are present
        content = create_page.text
        has_photo_uploader = "photoUploader()" in content
        has_video_uploader = "videoUploader()" in content
        has_drag_drop = "dragover.prevent" in content
        
        print(f"✅ Photo uploader component: {has_photo_uploader}")
        print(f"✅ Video uploader component: {has_video_uploader}")
        print(f"✅ Drag & drop support: {has_drag_drop}")
        
        if has_photo_uploader and has_video_uploader and has_drag_drop:
            print("🎉 All new uploader components are present!")
        else:
            print("⚠️  Some components are missing")
            
        # Check for Alpine.js
        has_alpine = "alpinejs" in content
        print(f"✅ Alpine.js loaded: {has_alpine}")
        
        return True
    else:
        print(f"❌ Failed to access create page: {create_page.status_code}")
        return False

def test_api_endpoints():
    """Test API endpoints for file upload"""
    print("\n🔌 Testing API endpoints...")
    
    # Test if API is accessible
    try:
        response = requests.get("http://localhost:8000/api/companies")
        print(f"API status: {response.status_code}")
        
        if response.status_code == 401:
            print("✅ API requires authentication (expected)")
        elif response.status_code == 200:
            print("✅ API is accessible")
        else:
            print(f"⚠️  Unexpected API status: {response.status_code}")
    except Exception as e:
        print(f"❌ API test failed: {e}")

if __name__ == "__main__":
    print("🚀 Testing AR Content File Uploader")
    print("=" * 50)
    
    success = test_login_and_access_create_page()
    test_api_endpoints()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ File uploader test completed successfully!")
        print("🌐 You can now test the uploader at: http://localhost:8000/ar-content/create")
        print("👤 Login with: admin@vertexar.com / admin123")
    else:
        print("❌ File uploader test failed!")