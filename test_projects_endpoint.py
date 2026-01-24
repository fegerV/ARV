#!/usr/bin/env python3
"""Test the /projects endpoint."""
import asyncio
from app.main import app
from fastapi.testclient import TestClient

def test_projects_endpoint():
    client = TestClient(app)
    
    # Try to access /projects
    try:
        response = client.get("/projects")
        print(f"Status code: {response.status_code}")
        if response.status_code != 200:
            print(f"Response: {response.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_projects_endpoint()
