#!/usr/bin/env python3
"""
Test script to verify AR Content schema and functionality.
This script checks that all required columns exist and AR content can be created successfully.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.core.database import get_async_session
from app.models.ar_content import ARContent
from app.models.company import Company
from app.models.project import Project
from app.models import ArContentStatus


async def check_ar_content_schema():
    """Check that all required columns exist in the ar_content table"""
    print("🔍 Checking AR Content table schema...")
    
    async for session in get_async_session():
        try:
            # Get column information
            result = await session.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'ar_content'
                ORDER BY ordinal_position
            """))
            columns = result.fetchall()
            
            print(f"✅ Found {len(columns)} columns in ar_content table")
            
            # Check for required columns
            required_columns = {
                'id', 'project_id', 'company_id', 'active_video_id', 'unique_id',
                'order_number', 'customer_name', 'customer_phone', 'customer_email',
                'duration_years', 'views_count', 'status', 'content_metadata',
                'photo_path', 'photo_url', 'thumbnail_url', 'video_path', 'video_url',
                'qr_code_path', 'qr_code_url', 'marker_path', 'marker_url', 
                'marker_status', 'marker_metadata', 'created_at', 'updated_at'
            }
            
            found_columns = {col[0] for col in columns}
            
            missing_columns = required_columns - found_columns
            if missing_columns:
                print(f"❌ Missing columns: {missing_columns}")
                return False
            else:
                print("✅ All required columns present")
            
            # Check for timestamp columns specifically
            timestamp_columns = [col for col in columns if col[0] in ['created_at', 'updated_at']]
            for col_name, data_type, is_nullable, column_default in timestamp_columns:
                if col_name in ['created_at', 'updated_at']:
                    print(f"✅ {col_name}: {data_type} (nullable: {is_nullable}, default: {column_default})")
            
            # Check for indexes
            index_result = await session.execute(text("""
                SELECT indexname FROM pg_indexes WHERE tablename = 'ar_content'
            """))
            indexes = [row[0] for row in index_result.fetchall()]
            print(f"✅ Found {len(indexes)} indexes: {indexes}")
            
            break
            
        except Exception as e:
            print(f"❌ Error checking schema: {e}")
            return False
    
    return True


async def test_ar_content_creation():
    """Test creating AR content records"""
    print("\n🧪 Testing AR Content creation...")
    
    async for session in get_async_session():
        try:
            # First, ensure we have a company and project
            company_result = await session.execute(
                text("SELECT id FROM companies LIMIT 1")
            )
            company = company_result.fetchone()
            
            if not company:
                print("❌ No company found. Creating test company...")
                await session.execute(text("""
                    INSERT INTO companies (name, slug, contact_email, status, created_at, updated_at)
                    VALUES ('Test Company', 'test-company', 'test@example.com', 'active', NOW(), NOW())
                    RETURNING id
                """))
                await session.commit()
                company_result = await session.execute(text("SELECT id FROM companies LIMIT 1"))
                company = company_result.fetchone()
            
            company_id = company[0]
            print(f"✅ Using company ID: {company_id}")
            
            # Check for project
            project_result = await session.execute(
                text("SELECT id FROM projects WHERE company_id = :company_id LIMIT 1"),
                {"company_id": company_id}
            )
            project = project_result.fetchone()
            
            if not project:
                print("❌ No project found. Creating test project...")
                await session.execute(text("""
                    INSERT INTO projects (name, status, company_id, created_at, updated_at)
                    VALUES ('Test Project', 'active', :company_id, NOW(), NOW())
                    RETURNING id
                """), {"company_id": company_id})
                await session.commit()
                project_result = await session.execute(
                    text("SELECT id FROM projects WHERE company_id = :company_id LIMIT 1"),
                    {"company_id": company_id}
                )
                project = project_result.fetchone()
            
            project_id = project[0]
            print(f"✅ Using project ID: {project_id}")
            
            # Test creating AR content
            print("📝 Creating test AR content...")
            
            test_data = {
                'project_id': project_id,
                'company_id': company_id,
                'order_number': f'TEST-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'customer_name': 'Test Customer',
                'customer_email': 'test@example.com',
                'customer_phone': '+1234567890',
                'duration_years': 1,
                'views_count': 0,
                'status': ArContentStatus.PENDING,
                'content_metadata': {'test': True, 'source': 'schema_test'},
                'photo_path': '/test/photo.jpg',
                'photo_url': 'https://example.com/photo.jpg',
                'thumbnail_url': 'https://example.com/thumb.jpg',
                'video_path': '/test/video.mp4',
                'video_url': 'https://example.com/video.mp4',
                'qr_code_path': '/test/qr.png',
                'qr_code_url': 'https://example.com/qr.png',
                'marker_path': '/test/marker.patt',
                'marker_url': 'https://example.com/marker.patt',
                'marker_status': 'pending',
                'marker_metadata': {'version': '1.0', 'type': 'mindar'}
            }
            
            # Insert test AR content
            insert_stmt = text("""
                INSERT INTO ar_content (
                    project_id, company_id, order_number, customer_name, customer_email, customer_phone,
                    duration_years, views_count, status, content_metadata, photo_path, photo_url,
                    thumbnail_url, video_path, video_url, qr_code_path, qr_code_url, marker_path,
                    marker_url, marker_status, marker_metadata, created_at, updated_at
                ) VALUES (
                    :project_id, :company_id, :order_number, :customer_name, :customer_email, :customer_phone,
                    :duration_years, :views_count, :status, :content_metadata, :photo_path, :photo_url,
                    :thumbnail_url, :video_path, :video_url, :qr_code_path, :qr_code_url, :marker_path,
                    :marker_url, :marker_status, :marker_metadata, NOW(), NOW()
                )
                RETURNING id, created_at, updated_at
            """)
            
            result = await session.execute(insert_stmt, test_data)
            await session.commit()
            
            ar_content = result.fetchone()
            ar_content_id = ar_content[0]
            created_at = ar_content[1]
            updated_at = ar_content[2]
            
            print(f"✅ AR Content created successfully!")
            print(f"   ID: {ar_content_id}")
            print(f"   Created: {created_at}")
            print(f"   Updated: {updated_at}")
            
            # Verify the record was created with all fields
            verify_result = await session.execute(
                text("SELECT * FROM ar_content WHERE id = :id"),
                {"id": ar_content_id}
            )
            record = verify_result.fetchone()
            
            if record:
                print(f"✅ Record verified with {len(record)} fields")
                
                # Check specific fields
                columns = [desc[0] for desc in verify_result.cursor.description]
                record_dict = dict(zip(columns, record))
                
                # Check timestamp fields
                if record_dict.get('created_at') and record_dict.get('updated_at'):
                    print("✅ Timestamp fields are properly set")
                else:
                    print("❌ Timestamp fields are missing")
                    return False
                
                # Check marker fields
                if record_dict.get('marker_status') == 'pending':
                    print("✅ Marker fields are properly set")
                else:
                    print("❌ Marker fields have issues")
                    return False
                
                # Clean up - remove test record
                await session.execute(
                    text("DELETE FROM ar_content WHERE id = :id"),
                    {"id": ar_content_id}
                )
                await session.commit()
                print("🧹 Test record cleaned up")
                
            else:
                print("❌ Failed to verify created record")
                return False
                
            break
            
        except Exception as e:
            print(f"❌ Error testing AR content creation: {e}")
            await session.rollback()
            return False
    
    return True


async def main():
    """Main test function"""
    print("🚀 Starting AR Content Schema and Functionality Test")
    print("=" * 60)
    
    # Test 1: Check schema
    schema_ok = await check_ar_content_schema()
    
    if not schema_ok:
        print("\n❌ Schema validation failed")
        return False
    
    # Test 2: Test creation
    creation_ok = await test_ar_content_creation()
    
    if not creation_ok:
        print("\n❌ AR Content creation test failed")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All tests passed! AR Content schema and functionality are working correctly.")
    print("✅ Timestamps and columns have been successfully added.")
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)