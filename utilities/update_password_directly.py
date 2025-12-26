import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
import bcrypt

async def update_password_directly():
    """Update admin password directly in the database"""
    settings = get_settings()
    
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Raw SQL update to avoid bcrypt issues in the application
            from sqlalchemy import text
            
            # Generate bcrypt hash for "admin123"
            # Ensure password is less than 72 bytes
            password = "admin123"
            if len(password.encode('utf-8')) > 72:
                password = password[:72]
            
            # Create bcrypt hash
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            hashed_str = hashed.decode('utf-8')
            
            print(f"Generated hash: {hashed_str}")
            
            # Update the password directly in the database
            await session.execute(
                text("UPDATE users SET hashed_password = :hashed_password, login_attempts = 0, locked_until = NULL WHERE email = :email"),
                {
                    "hashed_password": hashed_str,
                    "email": "admin@vertexar.com"
                }
            )
            
            await session.commit()
            print("Password updated successfully!")
            print(f"New password: {password}")
            return True
            
        except Exception as e:
            print(f"Error updating password: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            return False
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(update_password_directly())