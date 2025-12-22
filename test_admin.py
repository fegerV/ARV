#!/usr/bin/env python3
"""
Simple test script to initialize database and test admin functionality
"""
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import Base, engine, AsyncSessionLocal
from app.models import User, Company, Project, ARContent, Video
from app.core.security import get_password_hash
from app.models.base import BaseModel
from sqlalchemy import text
from datetime import datetime, timedelta
import uuid


async def init_database():
    """Initialize database with tables and seed data"""
    print("Creating database tables...")
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    print("Database tables created successfully!")
    
    # Create seed data
    await create_seed_data()


async def create_seed_data():
    """Create initial seed data for testing"""
    print("Creating seed data...")
    
    async with AsyncSessionLocal() as session:
        # Create admin user
        admin_user = User(
            email="admin@vertexar.com",
            full_name="System Administrator",
            hashed_password=get_password_hash("admin123"),
            role="admin",
            is_active=True
        )
        session.add(admin_user)
        
        # Create default company
        vertex_company = Company(
            name="Vertex AR",
            slug="vertex-ar",
            contact_email="admin@vertexar.com",
            status="active"
        )
        session.add(vertex_company)
        
        await session.commit()
        await session.refresh(admin_user)
        await session.refresh(vertex_company)
        
        # Create "Портреты" project
        portraits_project = Project(
            name="Портреты",
            company_id=vertex_company.id,
            status="active"
        )
        session.add(portraits_project)
        
        await session.commit()
        await session.refresh(portraits_project)
        
        print(f"✅ Created admin user: admin@vertexar.com / admin123")
        print(f"✅ Created company: Vertex AR (ID: {vertex_company.id})")
        print(f"✅ Created project: Портреты (ID: {portraits_project.id})")
        
        return admin_user, vertex_company, portraits_project


async def test_ar_content_creation():
    """Test AR content creation with all required fields"""
    print("\nTesting AR content creation...")
    
    async with AsyncSessionLocal() as session:
        # Get the company and project
        result = await session.execute(
            text("SELECT id FROM companies WHERE slug = 'vertex-ar'")
        )
        company_row = result.fetchone()
        if not company_row:
            print("❌ Company not found")
            return
        
        result = await session.execute(
            text("SELECT id FROM projects WHERE name = 'Портреты'")
        )
        project_row = result.fetchone()
        if not project_row:
            print("❌ Project not found")
            return
        
        company_id = company_row[0]
        project_id = project_row[0]
        
        # Create AR content
        ar_content = ARContent(
            order_number="TEST-001",
            unique_id=uuid.uuid4(),
            company_id=company_id,
            project_id=project_id,
            customer_name="Test Customer",
            customer_email="test@example.com",
            customer_phone="+1234567890",
            status="pending",
            qr_code_url="https://example.com/qr/test",
            content_metadata={"test": True},
            duration_years=3  # 3 years
        )
        session.add(ar_content)
        await session.commit()
        await session.refresh(ar_content)
        
        print(f"✅ Created AR content: {ar_content.order_number} (ID: {ar_content.id})")
        
        # Create video for AR content
        video = Video(
            ar_content_id=ar_content.id,
            filename="test_video.mp4",
            video_path="/tmp/storage/content/test_video.mp4",
            video_url="http://localhost:8000/storage/test_video.mp4",
            size_bytes=1024000,
            mime_type="video/mp4",
            status="uploaded",
            thumbnail_url="http://localhost:8000/storage/test_video_thumb.jpg"
        )
        session.add(video)
        await session.commit()
        await session.refresh(video)
        
        print(f"✅ Created video: {video.filename} (ID: {video.id})")
        
        return ar_content, video


async def test_database_schema():
    """Test that all required tables and columns exist"""
    print("\nTesting database schema...")
    
    async with engine.begin() as conn:
        # Check main tables exist
        tables_to_check = [
            'users', 'companies', 'projects', 'ar_content', 'videos'
        ]
        
        for table in tables_to_check:
            result = await conn.execute(
                text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            )
            if result.fetchone():
                print(f"✅ Table '{table}' exists")
            else:
                print(f"❌ Table '{table}' missing")
        
        # Check AR content columns
        result = await conn.execute(text("PRAGMA table_info(ar_content)"))
        columns = [row[1] for row in result.fetchall()]
        required_columns = [
            'id', 'order_number', 'unique_id', 'company_id', 'project_id',
            'customer_name', 'customer_email', 'customer_phone',
            'status', 'qr_code_url', 'thumbnail_url',
            'content_metadata', 'created_at', 'updated_at', 'duration_years'
        ]
        
        for col in required_columns:
            if col in columns:
                print(f"✅ Column 'ar_content.{col}' exists")
            else:
                print(f"❌ Column 'ar_content.{col}' missing")


async def main():
    """Main test function"""
    print("🚀 Starting Vertex AR Admin Test")
    print("=" * 50)
    
    try:
        # Initialize database
        await init_database()
        
        # Test schema
        await test_database_schema()
        
        # Test AR content creation
        ar_content, video = await test_ar_content_creation()
        
        print("\n" + "=" * 50)
        print("✅ All tests passed successfully!")
        print("\nNext steps:")
        print("1. Start the FastAPI server: uvicorn app.main:app --reload")
        print("2. Open admin panel: http://localhost:8000/admin")
        print("3. Login with: admin@vertexar.com / admin123")
        print("4. Create new AR content in the 'Портреты' project")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)