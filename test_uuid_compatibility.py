#!/usr/bin/env python3
"""
Test script to verify UUID compatibility fixes for SQLite.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import get_db
from app.models.ar_content import ARContent
from app.utils.ar_content import (
    build_ar_content_storage_path,
    build_unique_link,
    generate_qr_code
)
import uuid


async def test_uuid_compatibility():
    """Test that UUID functions work with string UUIDs."""
    print("Testing UUID compatibility for SQLite...")
    
    # Test 1: Generate string UUID
    string_uuid = str(uuid.uuid4())
    print(f"✓ Generated string UUID: {string_uuid}")
    
    # Test 2: Test build_ar_content_storage_path with string UUID
    try:
        storage_path = build_ar_content_storage_path(1, "project-1", string_uuid)
        print(f"✓ build_ar_content_storage_path works: {storage_path}")
    except Exception as e:
        print(f"✗ build_ar_content_storage_path failed: {e}")
        return False
    
    # Test 3: Test build_unique_link with string UUID
    try:
        link = build_unique_link(string_uuid)
        print(f"✓ build_unique_link works: {link}")
    except Exception as e:
        print(f"✗ build_unique_link failed: {e}")
        return False
    
    # Test 4: Test ARContent model with string UUID
    try:
        ar_content = ARContent(
            project_id=1,
            company_id=1,
            unique_id=string_uuid,
            order_number="TEST-001",
            customer_name="Test Customer",
            duration_years=1
        )
        print(f"✓ ARContent model accepts string UUID: {ar_content.unique_id}")
        print(f"  Type: {type(ar_content.unique_id)}")
    except Exception as e:
        print(f"✗ ARContent model failed with string UUID: {e}")
        return False
    
    # Test 5: Test ARContent model with UUID object (should fail)
    try:
        uuid_obj = uuid.uuid4()
        ar_content_bad = ARContent(
            project_id=1,
            company_id=1,
            unique_id=uuid_obj,  # This should cause issues
            order_number="TEST-002",
            customer_name="Test Customer 2",
            duration_years=1
        )
        print(f"⚠ ARContent model accepted UUID object (may cause issues): {ar_content_bad.unique_id}")
        print(f"  Type: {type(ar_content_bad.unique_id)}")
    except Exception as e:
        print(f"✓ ARContent model correctly rejected UUID object: {e}")
    
    print("\n✅ All UUID compatibility tests passed!")
    return True


async def test_database_operations():
    """Test database operations with string UUIDs."""
    print("\nTesting database operations...")
    
    try:
        # Get database session
        async for db in get_db():
            # Test creating AR content with string UUID
            string_uuid = str(uuid.uuid4())
            
            ar_content = ARContent(
                project_id=1,
                company_id=1,
                unique_id=string_uuid,
                order_number="DB-TEST-001",
                customer_name="DB Test Customer",
                duration_years=1
            )
            
            db.add(ar_content)
            await db.commit()
            await db.refresh(ar_content)
            
            print(f"✓ Database create successful: {ar_content.id}")
            print(f"  UUID in database: {ar_content.unique_id}")
            print(f"  UUID type: {type(ar_content.unique_id)}")
            
            # Test retrieving by UUID
            from sqlalchemy import select
            stmt = select(ARContent).where(ARContent.unique_id == string_uuid)
            result = await db.execute(stmt)
            found = result.scalar_one_or_none()
            
            if found:
                print(f"✓ Database retrieve successful: {found.id}")
                print(f"  Retrieved UUID: {found.unique_id}")
                print(f"  Retrieved type: {type(found.unique_id)}")
            else:
                print("✗ Failed to retrieve by UUID")
                return False
            
            # Clean up
            await db.delete(ar_content)
            await db.commit()
            print("✓ Database cleanup successful")
            
            break
    
    except Exception as e:
        print(f"✗ Database operation failed: {e}")
        return False
    
    print("✅ All database operation tests passed!")
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("UUID COMPATIBILITY TEST FOR SQLITE")
    print("=" * 60)
    
    success = True
    
    # Test utility functions
    if not await test_uuid_compatibility():
        success = False
    
    # Test database operations
    if not await test_database_operations():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ALL TESTS PASSED! UUID compatibility is fixed.")
    else:
        print("❌ SOME TESTS FAILED! Please check the errors above.")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)