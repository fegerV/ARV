"""
Script to fix notifications table structure by removing old columns.
"""
import sqlite3
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.core.config import settings
import re


def fix_notifications_table():
    """Fix notifications table by removing old columns."""
    
    # Extract database path from DATABASE_URL
    db_url = settings.DATABASE_URL
    
    if db_url.startswith("sqlite"):
        # Extract database file path
        match = re.search(r'sqlite[^:]*:///(.+)', db_url)
        if match:
            db_path = match.group(1)
        else:
            # Try relative path
            db_path = db_url.replace("sqlite+aiosqlite:///./", "").replace("sqlite:///", "")
        
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.path.dirname(__file__), '../..', db_path)
        
        db_path = os.path.abspath(db_path)
        print(f"Database path: {db_path}")
        
        if not os.path.exists(db_path):
            print(f"ERROR: Database file not found: {db_path}")
            return False
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get table info
            cursor.execute("PRAGMA table_info(notifications)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            print(f"Current columns: {column_names}")
            
            # Remove old columns if they exist
            columns_to_remove = ['priority', 'recipient_id', 'sender_id', 'title', 'type', 'is_read', 'updated_at']
            
            for col in columns_to_remove:
                if col in column_names:
                    try:
                        # SQLite doesn't support DROP COLUMN directly, need to recreate table
                        print(f"Column '{col}' exists and needs to be removed")
                    except Exception as e:
                        print(f"Warning: Could not check column '{col}': {e}")
            
            # SQLite doesn't support DROP COLUMN in older versions
            # We need to recreate the table
            print("\nRecreating notifications table...")
            
            # Get all current data
            cursor.execute("SELECT * FROM notifications")
            rows = cursor.fetchall()
            print(f"Found {len(rows)} existing notifications")
            
            # Create new table structure
            cursor.execute("DROP TABLE IF EXISTS notifications_old")
            cursor.execute("ALTER TABLE notifications RENAME TO notifications_old")
            
            # Create new table with correct structure
            cursor.execute("""
                CREATE TABLE notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER,
                    project_id INTEGER,
                    ar_content_id INTEGER,
                    notification_type VARCHAR(50) NOT NULL,
                    email_sent BOOLEAN DEFAULT 0,
                    email_sent_at DATETIME,
                    email_error TEXT,
                    telegram_sent BOOLEAN DEFAULT 0,
                    telegram_sent_at DATETIME,
                    telegram_error TEXT,
                    subject VARCHAR(500),
                    message TEXT,
                    metadata JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Migrate data from old table
            if rows:
                print("Migrating existing notifications...")
                for row in rows:
                    # Map old columns to new structure
                    row_dict = dict(zip(column_names, row))
                    
                    # Extract values
                    notification_type = row_dict.get('notification_type') or row_dict.get('type', 'unknown')
                    subject = row_dict.get('subject') or row_dict.get('title', '')
                    message = row_dict.get('message', '')
                    company_id = row_dict.get('company_id')
                    project_id = row_dict.get('project_id')
                    ar_content_id = row_dict.get('ar_content_id')
                    metadata = row_dict.get('metadata') or row_dict.get('notification_metadata') or '{}'
                    created_at = row_dict.get('created_at')
                    
                    # Insert into new table
                    cursor.execute("""
                        INSERT INTO notifications (
                            company_id, project_id, ar_content_id, notification_type,
                            email_sent, telegram_sent, subject, message, metadata, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        company_id, project_id, ar_content_id, notification_type,
                        row_dict.get('email_sent', 0), row_dict.get('telegram_sent', 0),
                        subject, message, metadata, created_at
                    ))
            
            # Drop old table
            cursor.execute("DROP TABLE notifications_old")
            
            conn.commit()
            print("[OK] Notifications table fixed successfully!")
            
            # Verify
            cursor.execute("SELECT COUNT(*) FROM notifications")
            count = cursor.fetchone()[0]
            print(f"[OK] Total notifications in new table: {count}")
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"[ERROR] Error fixing notifications table: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print(f"[ERROR] This script only works with SQLite databases. Current: {db_url}")
        return False


if __name__ == "__main__":
    success = fix_notifications_table()
    sys.exit(0 if success else 1)
