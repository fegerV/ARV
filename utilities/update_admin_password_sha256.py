import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.core.security import get_password_hash
from app.models.user import User
from sqlalchemy import select

async def update_admin_password_sha256():
    """Update admin user password using SHA-256 instead of bcrypt"""
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
            
            # Create new password hash with SHA-256
            new_password = "admin123"
            user.hashed_password = get_password_hash(new_password)
            user.login_attempts = 0
            user.locked_until = None
            
            await session.commit()
            print(f"Password updated successfully for {user.email}")
            print(f"New password: {new_password}")
            return True
            
        except Exception as e:
            print(f"Error updating admin password: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(update_admin_password_sha256())