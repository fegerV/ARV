import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.core.database import Base

async def create_tables():
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("Tables created successfully!")

if __name__ == "__main__":
    asyncio.run(create_tables())