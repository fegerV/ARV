#!/usr/bin/env python3
"""
Create notifications table in SQLite database.
"""

import sqlite3
import json

def create_notifications_table():
    """Create notifications table in SQLite database."""
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect('test_vertex_ar.db')
        cursor = conn.cursor()
        
        # Drop existing table if it exists
        cursor.execute("DROP TABLE IF EXISTS notifications")
        
        # Create notifications table matching the model
        cursor.execute("""
            CREATE TABLE notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                project_id INTEGER,
                ar_content_id INTEGER,
                notification_type VARCHAR(50),
                email_sent BOOLEAN DEFAULT FALSE,
                email_sent_at DATETIME,
                email_error TEXT,
                telegram_sent BOOLEAN DEFAULT FALSE,
                telegram_sent_at DATETIME,
                telegram_error TEXT,
                subject VARCHAR(500),
                message TEXT,
                metadata JSON,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create test notifications
        notifications = [
            (1, 1, 1, "ar_content_created", False, None, None, False, None, None,
             "New AR Content Created", 
             "A new AR content item 'Product Demo' was created for Vertex AR Solutions",
             json.dumps({
                 "is_read": False,
                 "company_name": "Vertex AR Solutions",
                 "project_name": "Q4 Campaign",
                 "ar_content_name": "Product Demo"
             }),
             "2024-12-25 10:30:00"),
            
            (1, 1, 2, "storage_alert", False, None, None, False, None, None,
             "Storage Alert",
             "Storage usage for Vertex AR Solutions has reached 80% of allocated space",
             json.dumps({
                 "is_read": True,
                 "read_at": "2024-12-24T15:45:00",
                 "company_name": "Vertex AR Solutions",
                 "project_name": "Summer Sale",
                 "ar_content_name": None
             }),
             "2024-12-24 14:45:00"),
            
            (1, 1, 3, "video_processed", False, None, None, False, None, None,
             "Video Processing Complete",
             "Video processing for 'Marketing Video' has been completed successfully",
             json.dumps({
                 "is_read": False,
                 "company_name": "Vertex AR Solutions",
                 "project_name": "Product Launch",
                 "ar_content_name": "Marketing Video"
             }),
             "2024-12-25 09:15:00"),
            
            (1, 1, 4, "marker_generated", False, None, None, False, None, None,
             "AR Marker Generated",
             "MindAR marker for 'Customer Portrait' has been generated and is ready for use",
             json.dumps({
                 "is_read": False,
                 "company_name": "Vertex AR Solutions",
                 "project_name": "Portrait Sessions",
                 "ar_content_name": "Customer Portrait"
             }),
             "2024-12-25 08:45:00"),
            
            (1, 1, 5, "subscription_expiry", False, None, None, False, None, None,
             "Subscription Expiring Soon",
             "AR content 'Demo Content' subscription will expire in 7 days",
             json.dumps({
                 "is_read": True,
                 "read_at": "2024-12-23T12:30:00",
                 "company_name": "Vertex AR Solutions",
                 "project_name": "Demo Project",
                 "ar_content_name": "Demo Content"
             }),
             "2024-12-23 11:20:00")
        ]
        
        # Insert test data
        cursor.executemany("""
            INSERT INTO notifications (
                company_id, project_id, ar_content_id, notification_type,
                email_sent, email_sent_at, email_error, telegram_sent, 
                telegram_sent_at, telegram_error, subject, message, 
                metadata, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, notifications)
        
        conn.commit()
        print(f"✅ Created notifications table with {len(notifications)} test records")
        
        # Verify data
        cursor.execute("SELECT COUNT(*) FROM notifications")
        count = cursor.fetchone()[0]
        print(f"📊 Total notifications: {count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creating notifications table: {e}")
        return False

if __name__ == "__main__":
    create_notifications_table()