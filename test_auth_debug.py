#!/usr/bin/env python3
"""
Debug authentication by testing a simple route
"""
import asyncio
import httpx
import json

async def test_auth_debug():
    """Debug authentication"""
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(follow_redirects=False) as client:
        print("=== Authentication Debug Test ===")
        
        # Step 1: Login
        print("\n1. Logging in as admin")
        login_data = {
            "username": "admin@vertexar.com",
            "password": "admin123"
        }
        
        # Get login page
        login_page = await client.get(f"{base_url}/admin/login")
        print(f"Login page status: {login_page.status_code}")
        
        # Submit login form
        login_response = await client.post(
            f"{base_url}/admin/login-form",
            data=login_data,
            follow_redirects=False
        )
        print(f"Login response status: {login_response.status_code}")
        
        if login_response.status_code in [302, 303]:
            print("✅ Login successful, redirected")
            
            # Extract cookies
            cookies = login_response.cookies
            print(f"Cookies received: {dict(cookies)}")
            
            # Step 2: Test API endpoint with cookies
            print("\n2. Testing API endpoint with cookies")
            api_response = await client.get(f"{base_url}/api/companies", cookies=cookies)
            print(f"API response status: {api_response.status_code}")
            
            if api_response.status_code == 200:
                print("✅ API authentication works")
                data = api_response.json()
                print(f"   Companies count: {len(data.get('items', []))}")
            else:
                print(f"❌ API authentication failed: {api_response.text[:200]}")
            
            # Step 3: Test simple debug route with cookies
            print("\n3. Testing debug route with cookies")
            debug_response = await client.get(f"{base_url}/debug-auth", cookies=cookies)
            print(f"Debug response status: {debug_response.status_code}")
            print(f"Debug response: {debug_response.text[:200]}")
            
        else:
            print(f"❌ Login failed: {login_response.text[:200]}")


if __name__ == "__main__":
    asyncio.run(test_auth_debug())