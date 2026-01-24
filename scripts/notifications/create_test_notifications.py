"""
Script to create test notifications for the admin panel.
"""
import asyncio
import sys
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.notification import Notification

async def create_test_notifications():
    """Create test notifications for the admin panel."""
    
    # Create database connection
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Test notifications with realistic data
        notifications = [
            Notification(
                company_id=1,
                project_id=1,
                ar_content_id=1,
                notification_type="ar_content_created",
                subject="New AR Content Created",
                message="A new AR content item 'Product Demo' was created for Vertex AR Solutions",
                notification_metadata={
                    "is_read": False,
                    "company_name": "Vertex AR Solutions",
                    "project_name": "Q4 Campaign",
                    "ar_content_name": "Product Demo"
                },
                created_at=datetime(2024, 12, 25, 10, 30)
            ),
            Notification(
                company_id=1,
                project_id=1,
                ar_content_id=2,
                notification_type="storage_alert",
                subject="Storage Alert",
                message="Storage usage for Vertex AR Solutions has reached 80% of allocated space",
                notification_metadata={
                    "is_read": True,
                    "read_at": datetime(2024, 12, 24, 15, 45),
                    "company_name": "Vertex AR Solutions",
                    "project_name": "Summer Sale",
                    "ar_content_name": None
                },
                created_at=datetime(2024, 12, 24, 14, 45)
            ),
            Notification(
                company_id=1,
                project_id=1,
                ar_content_id=3,
                notification_type="video_processed",
                subject="Video Processing Complete",
                message="Video processing for 'Marketing Video' has been completed successfully",
                notification_metadata={
                    "is_read": False,
                    "company_name": "Vertex AR Solutions",
                    "project_name": "Product Launch",
                    "ar_content_name": "Marketing Video"
                },
                created_at=datetime(2024, 12, 25, 9, 15)
            ),
            Notification(
                company_id=1,
                project_id=1,
                ar_content_id=4,
                notification_type="marker_generated",
                subject="AR Marker Generated",
                message="MindAR marker for 'Customer Portrait' has been generated and is ready for use",
                notification_metadata={
                    "is_read": False,
                    "company_name": "Vertex AR Solutions",
                    "project_name": "Portrait Sessions",
                    "ar_content_name": "Customer Portrait"
                },
                created_at=datetime(2024, 12, 25, 8, 45)
            ),
            Notification(
                company_id=1,
                project_id=1,
                ar_content_id=5,
                notification_type="subscription_expiry",
                subject="Subscription Expiring Soon",
                message="AR content 'Demo Content' subscription will expire in 7 days",
                notification_metadata={
                    "is_read": True,
                    "read_at": datetime(2024, 12, 23, 12, 30),
                    "company_name": "Vertex AR Solutions",
                    "project_name": "Demo Project",
                    "ar_content_name": "Demo Content"
                },
                created_at=datetime(2024, 12, 23, 11, 20)
            )
        ]
        
        # Add notifications to database
        for notification in notifications:
            session.add(notification)
        
        await session.commit()
        print(f"Created {len(notifications)} test notifications")
        
        # Display created notifications
        print("\nCreated notifications:")
        for notification in notifications:
            meta = notification.notification_metadata or {}
            print(f"- {notification.subject} ({'Read' if meta.get('is_read') else 'Unread'})")

if __name__ == "__main__":
    asyncio.run(create_test_notifications())
