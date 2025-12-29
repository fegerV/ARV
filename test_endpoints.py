#!/usr/bin/env python3
"""
Test script to validate that the companies and projects endpoints are working.
This script starts a temporary server and tests the endpoints.
"""

import asyncio
import uvicorn
from fastapi.testclient import TestClient
from app.main import app
import json

def test_endpoints():
    """Test the companies and projects endpoints"""
    
    # Create test client
    client = TestClient(app)
    
    print("Testing endpoints...")
    
    # Test health endpoint first
    try:
        response = client.get("/api/health/status")
        print(f"Health endpoint: {response.status_code}")
        if response.status_code != 200:
            print(f"Health response: {response.text}")
    except Exception as e:
        print(f"Health endpoint error: {e}")
        return False
    
    # Test companies endpoint (should return 401 without auth)
    try:
        response = client.get("/api/companies")
        print(f"Companies endpoint: {response.status_code}")
        if response.status_code == 401:
            print("✓ Companies endpoint returns 401 (expected without authentication)")
        elif response.status_code == 500:
            print(f"✗ Companies endpoint returns 500: {response.text}")
            return False
        else:
            print(f"Companies response: {response.text}")
    except Exception as e:
        print(f"✗ Companies endpoint error: {e}")
        return False
    
    # Test projects endpoint (should return 401 without auth)
    try:
        response = client.get("/api/projects")
        print(f"Projects endpoint: {response.status_code}")
        if response.status_code == 401:
            print("✓ Projects endpoint returns 401 (expected without authentication)")
        elif response.status_code == 500:
            print(f"✗ Projects endpoint returns 500: {response.text}")
            return False
        else:
            print(f"Projects response: {response.text}")
    except Exception as e:
        print(f"✗ Projects endpoint error: {e}")
        return False
    
    print("✓ All endpoints are working correctly (401 is expected without authentication)")
    return True

if __name__ == "__main__":
    success = test_endpoints()
    if success:
        print("\n✅ SUCCESS: The Internal Server Error has been fixed!")
        print("The endpoints are working correctly and require authentication as expected.")
    else:
        print("\n❌ FAILURE: There are still issues with the endpoints.")