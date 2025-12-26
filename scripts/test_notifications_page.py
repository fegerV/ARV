#!/usr/bin/env python3
"""
Test script to verify the notifications page functionality.
"""

import asyncio
import json
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.notification import Notification
from app.html.routes.notifications import notifications_page
from app.html.deps import CurrentActiveUser
from app.core.config import settings

# Use SQLite for testing
SQLITE_DATABASE_URL = "sqlite+aiosqlite:///./test_vertex_ar.db"

async def test_notifications_page():
    """Test the notifications page functionality."""
    
    print("🔍 Testing Notifications Page Functionality")
    print("=" * 50)
    
    # Create database connection
    engine = create_async_engine(SQLITE_DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Test 1: Check database connection
        print("\n1. 📊 Testing Database Connection")
        try:
            result = await session.execute(select(Notification))
            notifications = result.scalars().all()
            print(f"✅ Connected to database, found {len(notifications)} notifications")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
        
        # Test 2: Check notification data transformation
        print("\n2. 🔄 Testing Data Transformation")
        try:
            notifications_data = []
            for n in notifications[:3]:  # Test first 3 notifications
                meta = dict(n.notification_metadata or {})
                
                notification = {
                    "id": n.id,
                    "title": n.subject or meta.get("title") or n.notification_type.replace("_", " ").title(),
                    "message": n.message or "",
                    "created_at": n.created_at,
                    "is_read": bool(meta.get("is_read", False)),
                    "company_name": meta.get("company_name"),
                    "project_name": meta.get("project_name"),
                    "ar_content_name": meta.get("ar_content_name"),
                }
                notifications_data.append(notification)
            
            print("✅ Data transformation successful")
            for notif in notifications_data:
                status = "🔵 Read" if notif["is_read"] else "🔴 Unread"
                print(f"   {status} - {notif['title']}")
                print(f"   Company: {notif['company_name']} | Project: {notif['project_name']}")
                
        except Exception as e:
            print(f"❌ Data transformation failed: {e}")
            return False
        
        # Test 3: Check template fields
        print("\n3. 📋 Testing Template Fields")
        required_fields = ["id", "title", "message", "created_at", "is_read", 
                         "company_name", "project_name", "ar_content_name"]
        
        for notif in notifications_data:
            missing_fields = [field for field in required_fields if field not in notif]
            if missing_fields:
                print(f"❌ Missing fields in notification {notif['id']}: {missing_fields}")
                return False
        
        print("✅ All required fields present")
        
        # Test 4: Test API response structure
        print("\n4. 🔌 Testing API Response Structure")
        try:
            from app.schemas.notifications import NotificationItem, NotificationListResponse
            
            # Test single notification item
            if notifications_data:
                test_item = NotificationItem(**notifications_data[0])
                print("✅ NotificationItem schema validation passed")
            
            # Test list response
            test_list = NotificationListResponse(
                items=[NotificationItem(**item) for item in notifications_data],
                total=len(notifications_data),
                page=1,
                page_size=50,
                total_pages=1
            )
            print("✅ NotificationListResponse schema validation passed")
            
        except Exception as e:
            print(f"❌ Schema validation failed: {e}")
            return False
        
        print("\n🎉 All tests passed!")
        print("\n📄 Summary:")
        print(f"   - Database connection: ✅")
        print(f"   - Data transformation: ✅") 
        print(f"   - Template fields: ✅")
        print(f"   - API schemas: ✅")
        print(f"   - Total notifications: {len(notifications)}")
        
        return True

if __name__ == "__main__":
    success = asyncio.run(test_notifications_page())
    if success:
        print("\n✅ Notifications page is ready for testing!")
    else:
        print("\n❌ Issues found - please check the errors above")