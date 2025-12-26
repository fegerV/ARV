#!/usr/bin/env python3
"""
Simple script to check notifications in the SQLite database.
"""

import sqlite3
import json

def check_notifications():
    """Check notifications in SQLite database."""
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect('test_vertex_ar.db')
        cursor = conn.cursor()
        
        # Check if notifications table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notifications';")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("❌ notifications table does not exist")
            return False
        
        # Get all notifications
        cursor.execute("SELECT * FROM notifications ORDER BY created_at DESC")
        notifications = cursor.fetchall()
        
        # Get column names
        cursor.execute("PRAGMA table_info(notifications)")
        columns = [column[1] for column in cursor.fetchall()]
        
        print(f"✅ Found {len(notifications)} notifications")
        print(f"📋 Columns: {', '.join(columns)}")
        print()
        
        if notifications:
            print("📨 Notifications:")
            for i, notif in enumerate(notifications, 1):
                notif_dict = dict(zip(columns, notif))
                metadata = {}
                if notif_dict.get('metadata'):
                    try:
                        metadata = json.loads(notif_dict['metadata'])
                    except:
                        metadata = notif_dict.get('metadata', {})
                
                is_read = metadata.get('is_read', False)
                status = "🔵 Read" if is_read else "🔴 Unread"
                company = metadata.get('company_name', 'Unknown')
                project = metadata.get('project_name', 'Unknown')
                ar_content = metadata.get('ar_content_name', '—')
                
                print(f"{i}. {status} - {notif_dict['subject']}")
                print(f"   Company: {company} | Project: {project} | AR: {ar_content}")
                print(f"   Message: {notif_dict['message'][:80]}...")
                print(f"   Created: {notif_dict['created_at']}")
                print()
        else:
            print("📭 No notifications found")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking notifications: {e}")
        return False

if __name__ == "__main__":
    check_notifications()