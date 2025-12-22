#!/usr/bin/env python3

import asyncio
import sys
from app.core.database import AsyncSessionLocal
from sqlalchemy import select, text

async def check_admin_user():
    try:
        session = AsyncSessionLocal()
        
        # Check if admin user exists
        result = await session.execute(select(text("email, full_name, role, is_active")).select_from(text("users")))
        users = result.fetchall()
        
        print("=== Current Users ===")
        if users:
            for user in users:
                print(f"Email: {user[0]}, Name: {user[1]}, Role: {user[2]}, Active: {user[3]}")
        else:
            print("No users found in database")
        
        # Check if admin user with expected email exists
        from app.core.config import settings
        result = await session.execute(
            select(text("email")).select_from(text("users")).where(text("email = :email")), 
            {"email": settings.ADMIN_EMAIL}
        )
        admin_user = result.scalar_one_or_none()
        
        if admin_user:
            print(f"\n✅ Admin user found: {admin_user}")
        else:
            print(f"\n❌ Admin user not found for email: {settings.ADMIN_EMAIL}")
            print("Creating admin user...")
            
            # Create admin user
            from app.core.security import get_password_hash
            from app.models.user import User
            
            admin_user = User(
                email=settings.ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.ADMIN_DEFAULT_PASSWORD),
                full_name="System Administrator",
                role="admin",
                is_active=True,
            )
            session.add(admin_user)
            await session.commit()
            print(f"✅ Admin user created: {settings.ADMIN_EMAIL} / {settings.ADMIN_DEFAULT_PASSWORD}")
        
        await session.close()
        return True
    except Exception as e:
        print(f"❌ Error checking admin user: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(check_admin_user())
    sys.exit(0 if success else 1)