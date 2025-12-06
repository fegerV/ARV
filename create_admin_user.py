import asyncio
import sys
import os
from sqlalchemy import text

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from app.core.config import settings

async def create_admin_user():
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL)
    
    # Create async session factory
    AsyncSessionLocal = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    async with AsyncSessionLocal() as session:
        # Check if admin user already exists
        result = await session.execute(
            text("SELECT 1 FROM users WHERE email = 'admin@vertexar.com'")
        )
        
        if not result.fetchone():
            # Create new admin user
            admin_user = User(
                email="admin@vertexar.com",
                hashed_password=get_password_hash("admin123"),
                full_name="Vertex AR Admin",
                role=UserRole.ADMIN,
                is_active=True,
                login_attempts=0
            )
            
            session.add(admin_user)
            await session.commit()
            print("Admin user created successfully!")
        else:
            # Update existing admin user
            await session.execute(
                text("UPDATE users SET hashed_password = :password, login_attempts = 0 WHERE email = 'admin@vertexar.com'"),
                {"password": get_password_hash("admin123")}
            )
            await session.commit()
            print("Admin user updated successfully!")

if __name__ == "__main__":
    asyncio.run(create_admin_user())