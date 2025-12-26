#!/usr/bin/env python3
"""Reset admin password script"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.core.security import get_password_hash
from app.models.user import User
from sqlalchemy import select

async def reset_admin_password():
    """Reset admin password to default"""
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
            
            # Reset password
            new_password = "admin123"
            user.hashed_password = get_password_hash(new_password)
            user.login_attempts = 0
            user.locked_until = None
            
            await session.commit()
            print(f"Password reset successfully for {user.email}")
            print(f"New password: {new_password}")
            return True
            
        except Exception as e:
            print(f"Error resetting password: {e}")
            return False
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset_admin_password())