#!/usr/bin/env python3
"""Initialize database tables and seed default data."""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import init_db, seed_defaults

async def main():
    print("Initializing database...")
    try:
        await init_db()
        print("Database initialized successfully!")
        
        print("Seeding default data...")
        await seed_defaults()
        print("Default data seeded successfully!")
    except Exception as e:
        print(f"Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())