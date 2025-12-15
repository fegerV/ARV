#!/usr/bin/env python3
"""
Seed script to initialize the database with admin user and default company.

This script can be run independently or used as part of the application startup.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from app.core.database import get_async_session
from app.models import User, Company
from app.enums import CompanyStatus

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_admin_user(session: AsyncSession) -> bool:
    """Create admin user if it doesn't exist"""
    try:
        # Check if admin user already exists
        result = await session.execute(
            "SELECT id FROM users WHERE email = 'admin@vertex.local'"
        )
        existing_user = result.fetchone()
        
        if existing_user:
            print("Admin user already exists: admin@vertex.local")
            return False
        
        # Hash the password
        admin_password_hash = pwd_context.hash("admin123")
        
        # Create admin user
        admin_user = User(
            email="admin@vertex.local",
            hashed_password=admin_password_hash,
            full_name="System Administrator",
            role="admin",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        session.add(admin_user)
        await session.commit()
        print("✅ Created admin user: admin@vertex.local")
        return True
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        await session.rollback()
        return False


async def create_default_company(session: AsyncSession) -> bool:
    """Create default company if it doesn't exist"""
    try:
        # Check if default company already exists
        result = await session.execute(
            "SELECT id FROM companies WHERE name = 'Vertex AR'"
        )
        existing_company = result.fetchone()
        
        if existing_company:
            print("Default company already exists: Vertex AR")
            return False
        
        # Create default company
        default_company = Company(
            name="Vertex AR",
            slug="vertex-ar",
            contact_email="admin@vertex.local",
            status=CompanyStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        session.add(default_company)
        await session.commit()
        print("✅ Created default company: Vertex AR")
        return True
        
    except Exception as e:
        print(f"❌ Error creating default company: {e}")
        await session.rollback()
        return False


async def main():
    """Main seed function"""
    print("🌱 Starting database seed...")
    
    try:
        # Get database session
        async for session in get_async_session():
            # Create admin user
            user_created = await create_admin_user(session)
            
            # Create default company
            company_created = await create_default_company(session)
            
            if user_created or company_created:
                print("✅ Database seeding completed successfully!")
            else:
                print("ℹ️  Database already seeded, no changes made")
            
            break
            
    except Exception as e:
        print(f"❌ Error during database seeding: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the seed script
    asyncio.run(main())