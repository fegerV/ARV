#!/usr/bin/env python3
"""
Script to create admin user for testing
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.user import User
from app.core.config import settings
from datetime import datetime
import hashlib

def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

async def create_admin_user():
    """Create admin user for testing"""
    
    # Create database connection
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Check if admin already exists
            admin_query = select(User).where(User.email == "admin@vertexar.com")
            admin_result = await session.execute(admin_query)
            existing_admin = admin_result.scalar_one_or_none()
            
            if existing_admin:
                print("✅ Admin user already exists:")
                print(f"   Email: {existing_admin.email}")
                print(f"   Role: {existing_admin.role}")
                print(f"   Active: {existing_admin.is_active}")
                return
            
            # Create admin user
            admin_user = User(
                email="admin@vertexar.com",
                hashed_password=hash_password("admin123"),
                full_name="Vertex AR Admin",
                role="admin",
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            session.add(admin_user)
            await session.commit()
            await session.refresh(admin_user)
            
            print("✅ Created admin user:")
            print(f"   Email: {admin_user.email}")
            print(f"   Role: {admin_user.role}")
            print(f"   Active: {admin_user.is_active}")
            print(f"   Password: admin123")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(create_admin_user())