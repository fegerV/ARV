#!/usr/bin/env python3
"""Script to add missing columns to ar_content table"""

import asyncio
import asyncpg
from app.core.config import settings

async def add_missing_columns():
    """Add missing columns to ar_content table"""
    
    # Parse database URL
    db_url = settings.DATABASE_URL
    # Extract connection details from postgresql+asyncpg://user:pass@host:port/db
    import re
    match = re.match(r'postgresql\+asyncpg://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
    if not match:
        print("Invalid database URL format")
        return
    
    user, password, host, port, database = match.groups()
    
    # Connect to database
    conn = await asyncpg.connect(
        host=host,
        port=int(port),
        user=user,
        password=password,
        database=database
    )
    
    try:
        # Add missing columns
        columns_to_add = [
            "ALTER TABLE ar_content ADD COLUMN IF NOT EXISTS thumbnail_url VARCHAR(500)",
            "ALTER TABLE ar_content ADD COLUMN IF NOT EXISTS marker_path VARCHAR(500)",
            "ALTER TABLE ar_content ADD COLUMN IF NOT EXISTS marker_url VARCHAR(500)",
            "ALTER TABLE ar_content ADD COLUMN IF NOT EXISTS marker_status VARCHAR(50) DEFAULT 'pending'",
            "ALTER TABLE ar_content ADD COLUMN IF NOT EXISTS marker_metadata JSON",
            "ALTER TABLE ar_content ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()",
            "ALTER TABLE ar_content ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()"
        ]
        
        for column_sql in columns_to_add:
            try:
                await conn.execute(column_sql)
                print(f"✅ Executed: {column_sql}")
            except Exception as e:
                print(f"❌ Failed: {column_sql} - {e}")
        
        # Verify table structure
        print("\n📋 Current ar_content table structure:")
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default 
            FROM information_schema.columns 
            WHERE table_name = 'ar_content' 
            ORDER BY ordinal_position
        """)
        
        for col in columns:
            print(f"  {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'})")
        
    finally:
        await conn.close()
    
    print("\n✅ Database schema update completed!")

if __name__ == "__main__":
    asyncio.run(add_missing_columns())