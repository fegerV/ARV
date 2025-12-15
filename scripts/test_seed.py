#!/usr/bin/env python3
"""
Test script to validate the seed data creation.

This script can be used to verify that the admin user and default company
are created correctly by the migration or seed script.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_session
from app.core.security import verify_password


async def test_admin_user():
    """Test that admin user exists and can authenticate"""
    print("🔍 Testing admin user...")
    
    try:
        async for session in get_async_session():
            # Check if admin user exists
            result = await session.execute(
                "SELECT id, email, hashed_password, full_name, role, is_active FROM users WHERE email = 'admin@vertex.local'"
            )
            admin_user = result.fetchone()
            
            if not admin_user:
                print("❌ Admin user not found")
                return False
            
            print(f"✅ Admin user found: {admin_user.email}")
            print(f"   Full name: {admin_user.full_name}")
            print(f"   Role: {admin_user.role}")
            print(f"   Active: {admin_user.is_active}")
            
            # Test password verification
            is_valid_password = verify_password("admin123", admin_user.hashed_password)
            if is_valid_password:
                print("✅ Admin password verification successful")
            else:
                print("❌ Admin password verification failed")
                return False
            
            break
            
    except Exception as e:
        print(f"❌ Error testing admin user: {e}")
        return False
    
    return True


async def test_default_company():
    """Test that default company exists"""
    print("\n🔍 Testing default company...")
    
    try:
        async for session in get_async_session():
            # Check if default company exists
            result = await session.execute(
                "SELECT id, name, slug, contact_email, status FROM companies WHERE name = 'Vertex AR'"
            )
            company = result.fetchone()
            
            if not company:
                print("❌ Default company not found")
                return False
            
            print(f"✅ Default company found: {company.name}")
            print(f"   Slug: {company.slug}")
            print(f"   Contact email: {company.contact_email}")
            print(f"   Status: {company.status}")
            
            break
            
    except Exception as e:
        print(f"❌ Error testing default company: {e}")
        return False
    
    return True


async def main():
    """Main test function"""
    print("🧪 Testing seed data validation...")
    
    # Test admin user
    admin_ok = await test_admin_user()
    
    # Test default company
    company_ok = await test_default_company()
    
    if admin_ok and company_ok:
        print("\n🎉 All seed data tests passed!")
        print("\n📝 Login credentials:")
        print("   Email: admin@vertex.local")
        print("   Password: admin123")
        return 0
    else:
        print("\n❌ Some seed data tests failed!")
        return 1


if __name__ == "__main__":
    # Run the test
    exit_code = asyncio.run(main())
    sys.exit(exit_code)