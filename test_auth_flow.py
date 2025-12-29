#!/usr/bin/env python3
"""
Test script to validate the full authentication flow and API endpoints.
"""

import asyncio
import uvicorn
from fastapi.testclient import TestClient
from app.main import app
import json

def test_authenticated_endpoints():
    """Test endpoints with authentication"""
    
    # Create test client
    client = TestClient(app)
    
    print("Testing authenticated endpoints...")
    
    # First login to get token
    login_data = {
        "username": "admin@vertex.local",
        "password": "admin123"
    }
    
    try:
        response = client.post("/api/auth/login", data=login_data)
        print(f"Login endpoint: {response.status_code}")
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            if access_token:
                print("✓ Successfully obtained access token")
                
                # Test companies with auth
                headers = {"Authorization": f"Bearer {access_token}"}
                response = client.get("/api/companies", headers=headers)
                print(f"Companies endpoint with auth: {response.status_code}")
                if response.status_code == 200:
                    companies_data = response.json()
                    print(f"✓ Companies data: {len(companies_data.get('items', []))} companies found")
                    for company in companies_data.get('items', []):
                        print(f"  - {company['name']} ({company['status']})")
                else:
                    print(f"✗ Companies endpoint failed: {response.text}")
                    return False
                
                # Test projects with auth
                response = client.get("/api/projects", headers=headers)
                print(f"Projects endpoint with auth: {response.status_code}")
                if response.status_code == 200:
                    projects_data = response.json()
                    print(f"✓ Projects data: {len(projects_data.get('items', []))} projects found")
                    for project in projects_data.get('items', []):
                        print(f"  - {project['name']} ({project['status']})")
                else:
                    print(f"✗ Projects endpoint failed: {response.text}")
                    return False
                    
                return True
            else:
                print("✗ No access token in login response")
                return False
        else:
            print(f"✗ Login failed: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Authentication test error: {e}")
        return False

if __name__ == "__main__":
    success = test_authenticated_endpoints()
    if success:
        print("\n✅ SUCCESS: Full authentication and API flow is working!")
    else:
        print("\n❌ FAILURE: Issues with authentication or API endpoints.")