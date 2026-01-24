#!/usr/bin/env python3
"""
Debug script to test login process
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.user import User
from app.api.routes.auth import verify_password

async def debug_login():
    """Debug login process"""
    
    DATABASE_URL = 'sqlite+aiosqlite:///./vertex_ar.db'
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        username = "admin@vertexar.com"
        password = "admin123"
        
        print(f"Testing login for: {username}")
        
        # Get user by email
        result = await session.execute(select(User).where(User.email == username))
        user = result.scalar_one_or_none()
        
        if not user:
            print("❌ User not found")
            return
        
        print(f"✅ Found user: {user.email} (ID: {user.id})")
        print(f"   Active: {user.is_active}")
        print(f"   Role: {user.role}")
        print(f"   Hashed password: {user.hashed_password[:50]}...")
        
        # Test password verification
        try:
            is_valid = verify_password(password, user.hashed_password)
            print(f"   Password verification result: {is_valid}")
        except Exception as e:
            print(f"   Password verification error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_login())
