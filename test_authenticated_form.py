#!/usr/bin/env python3
"""
Test AR Content Form with Authentication
"""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from app.main import app

def test_authenticated_form():
    """Test AR Content form with authentication"""
    print("🔍 Testing AR Content Form with Authentication...")
    
    client = TestClient(app)
    
    # First, try to login
    print("📝 Logging in...")
    login_data = {
        "username": "admin@vertexar.com",
        "password": "admin123"
    }
    
    # Try to login via login form
    login_response = client.post("/admin/login-form", data=login_data, follow_redirects=False)
    print(f"Login response status: {login_response.status_code}")
    
    if login_response.status_code in [302, 303]:
        # Follow the redirect to get the session cookie
        redirect_url = login_response.headers.get("location", "/")
        print(f"Redirecting to: {redirect_url}")
        
        # Get the redirected page (this should set the session cookie)
        dashboard_response = client.get(redirect_url)
        print(f"Dashboard status: {dashboard_response.status_code}")
        
        if dashboard_response.status_code == 200:
            print("✅ Successfully logged in")
            
            # Now try to access the AR Content form
            form_response = client.get("/ar-content/create")
            print(f"Form response status: {form_response.status_code}")
            
            if form_response.status_code == 200:
                html_content = form_response.text
                
                # Save HTML to a file for inspection
                with open("debug_authenticated_form.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                
                print("✅ Authenticated form HTML saved to debug_authenticated_form.html")
                
                # Check for specific elements
                checks = {
                    "Photo file input": 'id="photo_file"' in html_content,
                    "Video file input": 'id="video_file"' in html_content,
                    "Company dropdown": 'id="company_id"' in html_content,
                    "Project dropdown": 'id="project_id"' in html_content,
                    "Alpine.js x-data": 'x-data="arContentForm"' in html_content,
                    "Form tag": '<form' in html_content,
                    "Multipart form": 'enctype="multipart/form-data"' in html_content,
                    "JavaScript function": 'function arContentForm' in html_content
                }
                
                print("\n📋 Element Checks:")
                for check_name, result in checks.items():
                    status = "✅" if result else "❌"
                    print(f"{status} {check_name}: {result}")
                
                # Look for file input elements specifically
                print("\n🔍 Looking for file input elements...")
                lines = html_content.split('\n')
                for i, line in enumerate(lines):
                    if 'input' in line and 'type="file"' in line:
                        print(f"Line {i+1}: {line.strip()}")
                
                return True
            else:
                print(f"❌ Failed to access form: {form_response.status_code}")
                print(f"Response: {form_response.text[:500]}")
                return False
        else:
            print(f"❌ Failed to access dashboard: {dashboard_response.status_code}")
            return False
    else:
        print(f"❌ Login failed: {login_response.status_code}")
        print(f"Response: {login_response.text[:500]}")
        return False

if __name__ == "__main__":
    test_authenticated_form()