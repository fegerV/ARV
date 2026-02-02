"""
Simple script to create test notifications using create_notification function.
"""
import asyncio
import sys
import os
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.services.notification_service import create_notification


async def create_test_notifications():
    """Create test notifications using create_notification function."""
    
    # Create database connection using settings
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("Creating test notifications...")
        
        # Test notification 1: AR Content Created
        try:
            notification1 = await create_notification(
                db=session,
                notification_type="ar_content_created",
                subject="New AR Content Created",
                message="A new AR content item 'Product Demo' was created for Vertex AR Solutions",
                company_id=1,
                project_id=1,
                ar_content_id=1,
                metadata={
                    "is_read": False,
                    "company_name": "Vertex AR Solutions",
                    "project_name": "Q4 Campaign",
                    "ar_content_name": "Product Demo"
                }
            )
            print(f"[OK] Created notification: {notification1.id} - {notification1.subject}")
        except Exception as e:
            print(f"[ERROR] Error creating notification 1: {e}")
        
        # Test notification 2: Storage Alert
        try:
            notification2 = await create_notification(
                db=session,
                notification_type="storage_alert",
                subject="Storage Alert",
                message="Storage usage for Vertex AR Solutions has reached 80% of allocated space",
                company_id=1,
                metadata={
                    "is_read": True,
                    "read_at": datetime.now(timezone.utc).isoformat(),
                    "company_name": "Vertex AR Solutions"
                }
            )
            print(f"[OK] Created notification: {notification2.id} - {notification2.subject}")
        except Exception as e:
            print(f"[ERROR] Error creating notification 2: {e}")
        
        # Test notification 3: Marker Generated
        try:
            notification3 = await create_notification(
                db=session,
                notification_type="marker_generated",
                subject="AR Marker Generated",
                message="MindAR marker for 'Customer Portrait' has been generated and is ready for use",
                company_id=1,
                project_id=1,
                ar_content_id=2,
                metadata={
                    "is_read": False,
                    "company_name": "Vertex AR Solutions",
                    "project_name": "Portrait Sessions",
                    "ar_content_name": "Customer Portrait"
                }
            )
            print(f"[OK] Created notification: {notification3.id} - {notification3.subject}")
        except Exception as e:
            print(f"[ERROR] Error creating notification 3: {e}")
        
        # Test notification 4: Subscription Expiry
        try:
            notification4 = await create_notification(
                db=session,
                notification_type="subscription_expiry",
                subject="Subscription Expiring Soon",
                message="AR content 'Demo Content' subscription will expire in 7 days",
                company_id=1,
                project_id=1,
                ar_content_id=3,
                metadata={
                    "is_read": False,
                    "company_name": "Vertex AR Solutions",
                    "project_name": "Demo Project",
                    "ar_content_name": "Demo Content"
                }
            )
            print(f"[OK] Created notification: {notification4.id} - {notification4.subject}")
        except Exception as e:
            print(f"[ERROR] Error creating notification 4: {e}")
        
        # Test notification 5: Processing Error
        try:
            notification5 = await create_notification(
                db=session,
                notification_type="processing_error",
                subject="Processing Error",
                message="An error occurred while processing AR content 'Test Content'. Please check the logs.",
                company_id=1,
                project_id=1,
                ar_content_id=4,
                metadata={
                    "is_read": False,
                    "company_name": "Vertex AR Solutions",
                    "project_name": "Test Project",
                    "ar_content_name": "Test Content"
                }
            )
            print(f"[OK] Created notification: {notification5.id} - {notification5.subject}")
        except Exception as e:
            print(f"[ERROR] Error creating notification 5: {e}")
        
        print("\n[OK] Test notifications creation completed!")
        print("Check http://127.0.0.1:8000/notifications to see the notifications")


if __name__ == "__main__":
    asyncio.run(create_test_notifications())
