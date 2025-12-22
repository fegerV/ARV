#!/usr/bin/env python3

import asyncio
import httpx
import json
from urllib.parse import urljoin

async def test_admin_login():
    """Test admin login functionality"""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        try:
            # Test health endpoint first
            health_response = await client.get(f"{base_url}/api/health/status")
            print(f"✅ Health check: {health_response.status_code}")
            
            # Test login endpoint
            login_data = {
                "username": "admin@vertex.local",
                "password": "admin123"
            }
            
            login_response = await client.post(
                f"{base_url}/api/auth/login",
                data=login_data
            )
            
            print(f"Login response status: {login_response.status_code}")
            
            if login_response.status_code == 200:
                result = login_response.json()
                if "access_token" in result:
                    print(f"✅ Login successful! Token received: {result['access_token'][:50]}...")
                    
                    # Test protected endpoint with token
                    headers = {"Authorization": f"Bearer {result['access_token']}"}
                    me_response = await client.get(f"{base_url}/api/auth/me", headers=headers)
                    
                    if me_response.status_code == 200:
                        user_info = me_response.json()
                        print(f"✅ Protected endpoint accessible! User: {user_info.get('email', 'Unknown')}")
                    else:
                        print(f"❌ Protected endpoint failed: {me_response.status_code}")
                else:
                    print(f"❌ Login response missing token: {result}")
            else:
                print(f"❌ Login failed: {login_response.status_code}")
                print(f"Response: {login_response.text}")
                
        except Exception as e:
            print(f"❌ Error testing login: {e}")

if __name__ == "__main__":
    asyncio.run(test_admin_login())