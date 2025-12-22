#!/usr/bin/env python3

import asyncio
import httpx
from urllib.parse import urljoin

async def test_complete_form_login():
    """Test complete form-based login with proper cookie handling"""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            print("=== Testing Complete Form Login ===")
            
            # Step 1: Get login page
            print("1. Getting login page...")
            login_page_response = await client.get(f"{base_url}/admin/login")
            print(f"   Login page status: {login_page_response.status_code}")
            
            # Step 2: Submit login form (follow_redirects=True will handle the 303)
            print("2. Submitting login form...")
            login_data = {
                "username": "admin@vertex.local",
                "password": "admin123"
            }
            
            form_response = await client.post(
                f"{base_url}/api/auth/login-form",
                data=login_data
            )
            
            print(f"   Final response status: {form_response.status_code}")
            print(f"   Final URL: {form_response.url}")
            
            if form_response.status_code == 200:
                if "dashboard" in form_response.text.lower() and "Vertex AR" in form_response.text:
                    print("✅ Complete form login successful! Dashboard accessible.")
                    
                    # Test that we have the right cookies
                    if "access_token" in [cookie.name for cookie in client.cookies.jar]:
                        print("✅ Authentication cookie set correctly.")
                        return True
                    else:
                        print("❌ No authentication cookie found.")
                        return False
                else:
                    print("❌ Dashboard page doesn't look right")
                    print(f"   Response preview: {form_response.text[:200]}...")
                    return False
            else:
                print(f"❌ Login failed - status: {form_response.status_code}")
                print(f"   Response: {form_response.text[:500]}...")
                return False
                
        except Exception as e:
            print(f"❌ Error testing complete login: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    asyncio.run(test_complete_form_login())