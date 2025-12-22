#!/usr/bin/env python3

import asyncio
import httpx
from urllib.parse import urljoin

async def test_admin_login_flow():
    """Test complete admin login flow via HTML form"""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(follow_redirects=False) as client:
        try:
            print("=== Testing Admin Login Flow ===")
            
            # Step 1: Get login page
            print("1. Getting login page...")
            login_page_response = await client.get(f"{base_url}/admin/login")
            print(f"   Login page status: {login_page_response.status_code}")
            
            if login_page_response.status_code != 200:
                print(f"❌ Failed to get login page: {login_page_response.text}")
                return False
            
            # Step 2: Submit login form
            print("2. Submitting login form...")
            login_data = {
                "username": "admin@vertex.local",
                "password": "admin123"
            }
            
            form_response = await client.post(
                f"{base_url}/api/auth/login-form",
                data=login_data
            )
            
            print(f"   Form submit status: {form_response.status_code}")
            
            if form_response.status_code == 303:  # Redirect after successful login
                redirect_url = form_response.headers.get("location", "/admin")
                print(f"   Redirecting to: {redirect_url}")
                
                # Step 3: Follow redirect to admin dashboard
                print("3. Following redirect to admin dashboard...")
                dashboard_response = await client.get(
                    urljoin(base_url, redirect_url),
                    cookies=form_response.cookies
                )
                
                print(f"   Dashboard status: {dashboard_response.status_code}")
                
                if dashboard_response.status_code == 200:
                    if "Vertex AR" in dashboard_response.text and "dashboard" in dashboard_response.text.lower():
                        print("✅ Admin login successful! Dashboard accessible.")
                        return True
                    else:
                        print("❌ Dashboard page doesn't look right")
                        print(f"   Response preview: {dashboard_response.text[:200]}...")
                        return False
                else:
                    print(f"❌ Failed to access dashboard: {dashboard_response.status_code}")
                    print(f"   Response: {dashboard_response.text[:200]}...")
                    return False
            else:
                print(f"❌ Login failed - status: {form_response.status_code}")
                print(f"   Response: {form_response.text[:500]}...")
                return False
                
        except Exception as e:
            print(f"❌ Error testing login flow: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    asyncio.run(test_admin_login_flow())