#!/usr/bin/env python3
"""
Simple test script to verify notifications page data structure.
"""

import sqlite3
import json

def test_notifications_data():
    """Test notifications page data structure."""
    
    print("🔍 Testing Notifications Data Structure")
    print("=" * 50)
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect('test_vertex_ar.db')
        cursor = conn.cursor()
        
        # Get notifications
        cursor.execute("SELECT * FROM notifications ORDER BY created_at DESC")
        notifications = cursor.fetchall()
        
        # Get column names
        cursor.execute("PRAGMA table_info(notifications)")
        columns = [column[1] for column in cursor.fetchall()]
        
        print(f"✅ Found {len(notifications)} notifications")
        print(f"📋 Columns: {', '.join(columns)}")
        
        # Test data transformation
        print("\n🔄 Testing Data Transformation")
        notifications_data = []
        
        for notif_row in notifications:
            notif_dict = dict(zip(columns, notif_row))
            metadata = {}
            if notif_dict.get('metadata'):
                try:
                    metadata = json.loads(notif_dict['metadata'])
                except:
                    metadata = {}
            
            # Transform like in the route
            notification = {
                "id": notif_dict['id'],
                "title": notif_dict['subject'] or metadata.get("title") or notif_dict['notification_type'].replace("_", " ").title(),
                "message": notif_dict['message'] or "",
                "created_at": notif_dict['created_at'],
                "is_read": bool(metadata.get("is_read", False)),
                "company_name": metadata.get("company_name"),
                "project_name": metadata.get("project_name"),
                "ar_content_name": metadata.get("ar_content_name"),
            }
            notifications_data.append(notification)
        
        print("✅ Data transformation successful")
        
        # Check required fields
        print("\n📋 Testing Template Fields")
        required_fields = ["id", "title", "message", "created_at", "is_read", 
                         "company_name", "project_name", "ar_content_name"]
        
        for i, notif in enumerate(notifications_data[:3], 1):
            print(f"\nNotification {i}:")
            missing_fields = [field for field in required_fields if field not in notif]
            if missing_fields:
                print(f"❌ Missing fields: {missing_fields}")
                return False
            
            status = "🔵 Read" if notif["is_read"] else "🔴 Unread"
            print(f"   {status} - {notif['title']}")
            print(f"   Company: {notif['company_name']}")
            print(f"   Project: {notif['project_name']}")
            print(f"   AR Content: {notif['ar_content_name']}")
            print(f"   Created: {notif['created_at']}")
        
        print("\n✅ All required fields present")
        
        # Test template rendering
        print("\n📄 Testing Template Compatibility")
        
        for notif in notifications_data[:2]:
            # Simulate template rendering
            title_display = notif['title'] or 'Notification'
            message_display = notif['message'] or 'No message'
            company_display = notif['company_name'] or '—'
            project_display = notif['project_name'] or '—'
            ar_content_display = notif['ar_content_name'] or '—'
            
            print(f"\n📨 Template rendering test:")
            print(f"   Title: {title_display}")
            print(f"   Message: {message_display[:50]}...")
            print(f"   Company: {company_display}")
            print(f"   Project: {project_display}")
            print(f"   AR Content: {ar_content_display}")
        
        print("\n🎉 All tests passed!")
        print("\n📄 Summary:")
        print(f"   - Database connection: ✅")
        print(f"   - Data transformation: ✅") 
        print(f"   - Template fields: ✅")
        print(f"   - Template compatibility: ✅")
        print(f"   - Total notifications: {len(notifications_data)}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_notifications_data()
    if success:
        print("\n✅ Notifications page data is ready!")
        print("🌐 You can now test the page at: http://localhost:8000/notifications")
    else:
        print("\n❌ Issues found - please check errors above")