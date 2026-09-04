#!/usr/bin/env python3
"""Test AR content creation API endpoint"""

import asyncio
import io
from fastapi.testclient import TestClient
from fastapi import FastAPI
import multipart
from app.main import app
from app.core.database import get_db, AsyncSessionLocal
from app.models.user import User
from app.core.security import create_access_token

def get_test_db():
    """Test database session"""
    async def override_get_db():
        async with AsyncSessionLocal() as session:
            yield session
    return override_get_db

async def test_ar_content_api():
    """Test AR content creation API endpoint"""
    
    # Override database dependency
    app.dependency_overrides[get_db] = get_test_db()
    
    client = TestClient(app)
    
    # Create a test user and get token
    async with AsyncSessionLocal() as session:
        # Check if admin user exists
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.email == "admin@vertex.local"))
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            print("❌ Admin user not found. Please run seed data first.")
            return
        
        # Create access token
        token = create_access_token(data={"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {token}"}
    
    # Test data for AR content creation
    files = {
        "photo_file": ("test.jpg", io.BytesIO(b"fake image data"), "image/jpeg"),
        "video_file": ("test.mp4", io.BytesIO(b"fake video data"), "video/mp4")
    }
    
    data = {
        "company_id": "1",
        "project_id": "1", 
        "customer_name": "Test Customer",
        "customer_phone": "+1234567890",
        "customer_email": "test@example.com",
        "duration_years": "1"
    }
    
    try:
        print("🧪 Testing AR content creation API endpoint...")
        
        # Test the endpoint
        response = client.post(
            "/api/ar-content",
            headers=headers,
            files=files,
            data=data
        )
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📄 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ AR content creation successful!")
            print(f"🆔 ID: {result.get('id')}")
            print(f"📋 Order Number: {result.get('order_number')}")
            print(f"🔗 Public Link: {result.get('public_link')}")
            print(f"🖼️  Photo URL: {result.get('photo_url')}")
            print(f"🎥 Video URL: {result.get('video_url')}")
            print(f"📱 QR Code URL: {result.get('qr_code_url')}")
        else:
            print("❌ AR content creation failed!")
            print(f"📄 Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()

if __name__ == "__main__":
    asyncio.run(test_ar_content_api())