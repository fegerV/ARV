import asyncio
import sys
import os
from pathlib import Path
import hashlib

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.models.user import User
from sqlalchemy import select

async def check_hash_type():
    """Check the type of hash stored in the database"""
    settings = get_settings()
    
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Find admin user
            result = await session.execute(select(User).where(User.email == "admin@vertexar.com"))
            user = result.scalar_one_or_none()
            
            if not user:
                print("Admin user not found!")
                return False
                
            print(f"Found user: {user.email}")
            print(f"Current hash: {user.hashed_password}")
            print(f"Hash length: {len(user.hashed_password)}")
            
            # Check if it looks like bcrypt hash (starts with $2b$, $2a$, etc.)
            hash_value = user.hashed_password
            if hash_value.startswith('$2'):
                print("This is still a bcrypt hash!")
                print("Need to update it again with SHA-256")
                
                # Update again with SHA-256
                from app.core.security import get_password_hash
                new_hash = get_password_hash("admin123")
                user.hashed_password = new_hash
                user.login_attempts = 0
                user.locked_until = None
                
                await session.commit()
                print(f"Updated to SHA-256 hash: {new_hash}")
            else:
                print("This appears to be a SHA-256 hash")
            
            return True
            
        except Exception as e:
            print(f"Error checking hash: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_hash_type())