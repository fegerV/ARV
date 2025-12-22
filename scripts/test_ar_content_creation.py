#!/usr/bin/env python3
"""
Test script to verify AR content creation works correctly
"""
import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models.ar_content import ARContent
from app.core.database import get_async_session
from app.enums import ArContentStatus
from sqlalchemy import text


async def test_ar_content_creation():
    """Test that AR content can be created successfully"""
    print("Testing AR content creation...")
    
    async for session in get_async_session():
        try:
            # Test creating a simple AR content record
            ar_content = ARContent(
                project_id=1,
                company_id=1,
                order_number="TEST-001",
                customer_name="Test Customer",
                duration_years=1,
                views_count=0,
                status=ArContentStatus.PENDING
            )
            
            session.add(ar_content)
            await session.commit()
            await session.refresh(ar_content)
            
            print(f"✅ Successfully created AR content with ID: {ar_content.id}")
            print(f"   Created at: {ar_content.created_at}")
            print(f"   Updated at: {ar_content.updated_at}")
            print(f"   Unique ID: {ar_content.unique_id}")
            
            # Clean up the test record
            await session.delete(ar_content)
            await session.commit()
            print("✅ Test record cleaned up successfully")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating AR content: {e}")
            await session.rollback()
            return False
        finally:
            await session.close()


async def test_database_connection():
    """Test database connection and verify table structure"""
    print("Testing database connection...")
    
    async for session in get_async_session():
        try:
            # Check if ar_content table exists and has the required columns
            result = await session.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'ar_content' 
                AND column_name IN ('created_at', 'updated_at')
                ORDER BY column_name
            """))
            
            columns = result.fetchall()
            
            if len(columns) == 2:
                print("✅ Database connection successful")
                print("✅ ar_content table has required timestamp columns:")
                for col in columns:
                    print(f"   - {col[0]}: {col[1]}")
                return True
            else:
                print(f"❌ Missing timestamp columns. Found: {[col[0] for col in columns]}")
                return False
                
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            return False
        finally:
            await session.close()


async def main():
    """Main test function"""
    print("🔧 AR Content Creation Debug Test")
    print("=" * 50)
    
    # Test database connection first
    if not await test_database_connection():
        print("\n❌ Database tests failed. Cannot proceed with AR content creation test.")
        return False
    
    print("\n" + "=" * 50)
    
    # Test AR content creation
    if await test_ar_content_creation():
        print("\n🎉 All tests passed! AR content creation issue has been resolved.")
        return True
    else:
        print("\n❌ AR content creation test failed.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)