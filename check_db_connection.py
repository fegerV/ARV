#!/usr/bin/env python3

import asyncio
import sys
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def check_db():
    try:
        session = AsyncSessionLocal()
        result = await session.execute(text('SELECT version()'))
        version = result.scalar()
        print(f"✅ Database connected successfully!")
        print(f"PostgreSQL version: {version}")
        
        # Check if tables exist
        result = await session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]
        print(f"Tables found: {tables}")
        
        await session.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(check_db())
    sys.exit(0 if success else 1)