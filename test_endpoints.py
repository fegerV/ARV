#!/usr/bin/env python3
"""
Endpoint Testing Script for Vertex AR B2B Platform
Tests all backend API endpoints and reports their status
"""

import asyncio
import sys
import httpx
import json
from pathlib import Path
from typing import Dict, List, Any

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.main import app
from app.core.config import get_settings

settings = get_settings()

class EndpointTester:
    def __init__(self):
        self.base_url = f"http://{settings.API_HOST}:{settings.API_PORT}"
        self.results = []
        self.auth_token = None
        
    async def test_endpoint(self, method: str, url: str, auth_required: bool = False, data: Dict = None) -> Dict[str, Any]:
        """Test a single endpoint"""
        full_url = f"{self.base_url}{url}"
        headers = {}
        
        if auth_required and self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if method.upper() == "GET":
                    response = await client.get(full_url, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(full_url, headers=headers, json=data)
                elif method.upper() == "PUT":
                    response = await client.put(full_url, headers=headers, json=data)
                elif method.upper() == "DELETE":
                    response = await client.delete(full_url, headers=headers)
                else:
                    return {"status": "error", "message": f"Unsupported method: {method}"}
                
                return {
                    "status": "success" if response.status_code < 400 else "error",
                    "status_code": response.status_code,
                    "response": response.text[:500] if response.text else "",
                    "url": full_url,
                    "method": method
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "url": full_url,
                "method": method
            }
    
    async def login(self):
        """Login to get auth token"""
        login_data = {
            "username": "admin@vertex.local",
            "password": "admin123"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/auth/login",
                    data=login_data
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    self.auth_token = token_data.get("access_token")
                    print(f"✅ Login successful, token received")
                    return True
                else:
                    print(f"❌ Login failed: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    async def run_tests(self):
        """Run all endpoint tests"""
        print("🚀 Starting Endpoint Testing...")
        print(f"📍 Base URL: {self.base_url}")
        
        # Define all endpoints to test
        endpoints = [
            # Health endpoints (no auth)
            {"method": "GET", "url": "/api/health/status", "auth": False},
            {"method": "GET", "url": "/", "auth": False},
            
            # Auth endpoints
            {"method": "POST", "url": "/api/auth/login", "auth": False, "data": {"username": "admin@vertex.local", "password": "admin123"}},
            
            # Companies endpoints
            {"method": "GET", "url": "/api/companies/", "auth": True},
            {"method": "POST", "url": "/api/companies/", "auth": True, "data": {"name": "Test Company", "slug": "test-company"}},
            
            # Projects endpoints
            {"method": "GET", "url": "/api/projects/projects", "auth": True},
            {"method": "GET", "url": "/api/projects/companies/1/projects", "auth": True},
            
            # AR Content endpoints
            {"method": "GET", "url": "/api/ar-content/companies/1/projects/1/ar-content", "auth": False},
            
            # Storage endpoints
            {"method": "GET", "url": "/api/storage/storage/connections", "auth": False},
            
            # Analytics endpoints
            {"method": "GET", "url": "/api/analytics/analytics/overview", "auth": False},
            
            # Notifications endpoints
            {"method": "GET", "url": "/api/notifications/notifications", "auth": True},
            
            # Settings endpoints
            {"method": "GET", "url": "/api/settings/settings", "auth": False},
            
            # Public endpoints
            {"method": "GET", "url": "/api/public/ar/test-unique-id/content", "auth": False},
        ]
        
        # First try to login
        await self.login()
        
        print("\n📋 Testing Endpoints:")
        print("=" * 80)
        
        for endpoint in endpoints:
            result = await self.test_endpoint(
                endpoint["method"],
                endpoint["url"],
                endpoint.get("auth", False),
                endpoint.get("data")
            )
            
            status_icon = "✅" if result["status"] == "success" else "❌"
            auth_info = "🔒" if endpoint.get("auth", False) else "🌐"
            
            print(f"{status_icon} {auth_info} {endpoint['method']:4} {endpoint['url']}")
            if result["status"] == "error":
                print(f"    Error: {result.get('message', 'Unknown error')}")
            elif result.get("status_code", 200) >= 400:
                print(f"    HTTP {result['status_code']}: {result.get('response', '')[:100]}")
            
            self.results.append({
                **endpoint,
                **result
            })
        
        print("\n" + "=" * 80)
        print("📊 Test Summary:")
        
        success_count = sum(1 for r in self.results if r["status"] == "success")
        error_count = len(self.results) - success_count
        
        print(f"✅ Success: {success_count}")
        print(f"❌ Errors:  {error_count}")
        print(f"📈 Total:   {len(self.results)}")
        
        # Save results to file
        with open("endpoint_test_results.json", "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to endpoint_test_results.json")

if __name__ == "__main__":
    tester = EndpointTester()
    asyncio.run(tester.run_tests())