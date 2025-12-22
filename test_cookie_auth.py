#!/usr/bin/env python3

import asyncio
import httpx
from urllib.parse import urljoin

async def test_cookie_auth():
    """Test cookie authentication directly"""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        try:
            print("=== Testing Cookie Authentication ===")
            
            # Step 1: Login via API to get token
            print("1. Getting token via API...")
            login_data = {
                "username": "admin@vertex.local",
                "password": "admin123"
            }
            
            api_response = await client.post(f"{base_url}/api/auth/login", data=login_data)
            
            if api_response.status_code != 200:
                print(f"❌ API login failed: {api_response.status_code}")
                print(f"   Response: {api_response.text}")
                return False
            
            token_data = api_response.json()
            access_token = token_data.get("access_token")
            print(f"   Got token: {access_token[:50]}...")
            
            # Step 2: Set cookie manually and test admin route
            print("2. Setting cookie and testing admin route...")
            client.cookies.set("access_token", access_token)
            
            admin_response = await client.get(f"{base_url}/admin")
            print(f"   Admin route status: {admin_response.status_code}")
            
            if admin_response.status_code == 200:
                if "dashboard" in admin_response.text.lower():
                    print("✅ Admin dashboard accessible with cookie!")
                    return True
                else:
                    print("❌ Dashboard response doesn't look right")
                    return False
            else:
                print(f"❌ Admin route failed: {admin_response.status_code}")
                print(f"   Response: {admin_response.text[:200]}...")
                return False
                
        except Exception as e:
            print(f"❌ Error testing cookie auth: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    asyncio.run(test_cookie_auth())