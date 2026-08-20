#!/usr/bin/env python3
"""Create admin user script"""

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

async def create_admin_user():
    """Create admin user with password from ADMIN_DEFAULT_PASSWORD env var"""
    settings = get_settings()
    new_password = os.environ.get("ADMIN_DEFAULT_PASSWORD", "")
    if not new_password:
        print("Error: ADMIN_DEFAULT_PASSWORD environment variable is not set")
        return False
    
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Check if admin user already exists
            result = await session.execute(select(User).where(User.email == "admin@vertexar.com"))
            user = result.scalar_one_or_none()
            
            if user:
                print(f"Admin user already exists: {user.email}")
                # Update password
                user.hashed_password = get_password_hash(new_password)
                user.login_attempts = 0
                user.locked_until = None
                print(f"Password updated for {user.email}")
            else:
                # Create new admin user
                user = User(
                    email="admin@vertexar.com",
                    hashed_password=get_password_hash(new_password),
                    full_name="Vertex AR Admin",
                    role="admin",
                    is_active=True,
                    login_attempts=0
                )
                session.add(user)
                print(f"Created new admin user: {user.email}")
            
            await session.commit()
            return True
            
        except Exception as e:
            print(f"Error creating/updating admin user: {e}")
            return False
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_admin_user())