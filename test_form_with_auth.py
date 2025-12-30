#!/usr/bin/env python3
"""
Test AR Content Form with authentication
"""

import asyncio
import aiohttp
import json
from base64 import b64encode

async def test_ar_content_form():
    """Test AR Content Form with authentication"""
    
    print("🔍 Testing AR Content Form with authentication...")
    
    async with aiohttp.ClientSession() as session:
        # Login first
        login_data = {
            "username": "admin@vertex.local", 
            "password": "admin123"
        }
        
        async with session.post("http://localhost:8000/admin/login-form", data=login_data) as response:
            if response.status == 200:
                print("✅ Login successful")
                # Get cookies from login response
                cookies = response.cookies
            else:
                print(f"❌ Login failed: {response.status}")
                return
        
        # Test AR Content Form page
        async with session.get("http://localhost:8000/ar-content/create", cookies=cookies) as response:
            if response.status == 200:
                content = await response.text()
                print("✅ AR Content Form page loaded successfully")
                
                # Check for form elements
                if "Компания" in content:
                    print("✅ Company field found")
                else:
                    print("❌ Company field missing")
                
                if "Проект" in content:
                    print("✅ Project field found") 
                else:
                    print("❌ Project field missing")
                
                if "Создать AR контент" in content:
                    print("✅ Create button found")
                else:
                    print("❌ Create button missing")
                
                # Check for data in form
                if "Vertex AR" in content:
                    print("✅ Company data found in form")
                else:
                    print("❌ Company data missing from form")
                
                if "Портреты" in content:
                    print("✅ Project data found in form")
                else:
                    print("❌ Project data missing from form")
                
                # Save HTML for inspection
                with open('/tmp/ar_content_form.html', 'w') as f:
                    f.write(content)
                print("💾 Form HTML saved to /tmp/ar_content_form.html")
                
            else:
                print(f"❌ Failed to load form: {response.status}")
                return

if __name__ == "__main__":
    asyncio.run(test_ar_content_form())