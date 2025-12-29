#!/usr/bin/env python3
"""
Debug File Upload Error
"""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from app.main import app
import io
from PIL import Image

def debug_file_upload():
    """Debug file upload with detailed error reporting"""
    print("🔍 Debugging File Upload Error...")
    
    client = TestClient(app)
    
    # Login first
    print("📝 Logging in...")
    login_data = {
        "username": "admin@vertexar.com",
        "password": "admin123"
    }
    
    login_response = client.post("/admin/login-form", data=login_data, follow_redirects=False)
    print(f"Login response status: {login_response.status_code}")
    
    if login_response.status_code in [302, 303]:
        # Get the session cookie from the login response
        cookies = login_response.cookies
        
        # Test with simple form data first (no files)
        print("📝 Testing simple form submission...")
        
        form_data = {
            'company_id': '1',
            'project_id': '1',
            'customer_name': 'Test Customer',
            'customer_phone': '+7 (999) 123-45-67',
            'customer_email': 'test@example.com',
            'duration_years': '3'
        }
        
        simple_response = client.post(
            "/companies/1/projects/1/ar-content",
            data=form_data,
            cookies=cookies
        )
        
        print(f"Simple form response status: {simple_response.status_code}")
        if simple_response.status_code != 200:
            print(f"Simple form error: {simple_response.text[:500]}")
        
        # Test with files
        print("📤 Testing file upload...")
        
        # Create a test image
        test_image = Image.new('RGB', (100, 100), color='red')
        image_bytes = io.BytesIO()
        test_image.save(image_bytes, format='PNG')
        image_bytes.seek(0)
        
        # Create test video content (just a dummy file)
        test_video_content = b"fake video content for testing"
        
        # Prepare files
        files = {
            'photo_file': ('test.png', image_bytes, 'image/png'),
            'video_file': ('test.mp4', test_video_content, 'video/mp4')
        }
        
        # Submit form with files
        upload_response = client.post(
            "/companies/1/projects/1/ar-content",
            files=files,
            data=form_data,
            cookies=cookies
        )
        
        print(f"Upload response status: {upload_response.status_code}")
        print(f"Upload response headers: {dict(upload_response.headers)}")
        
        if upload_response.status_code != 200:
            print(f"Upload error: {upload_response.text}")
        else:
            print("✅ File upload successful!")
            result = upload_response.json()
            print(f"Response: {result}")
        
        # Check alternative endpoints
        print("\n🔍 Checking alternative endpoints...")
        
        # Try direct API endpoint
        api_response = client.post(
            "/api/ar-content",
            files=files,
            data=form_data,
            cookies=cookies
        )
        
        print(f"API endpoint response status: {api_response.status_code}")
        if api_response.status_code != 200:
            print(f"API error: {api_response.text[:500]}")
        
    else:
        print(f"❌ Login failed: {login_response.status_code}")
        print(f"Response: {login_response.text[:500]}")

if __name__ == "__main__":
    debug_file_upload()