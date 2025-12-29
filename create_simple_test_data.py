#!/usr/bin/env python3
"""
Create simple test data for AR Content testing
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import AsyncSessionLocal
from app.models.company import Company
from app.models.project import Project
from app.models.user import User
from app.models.ar_content import ARContent
from app.core.security import get_password_hash
from app.enums import CompanyStatus, ProjectStatus, ArContentStatus
from sqlalchemy import select

async def create_test_data():
    """Create test data"""
    print("🚀 Creating test data...")
    
    async with AsyncSessionLocal() as db:
        try:
            # Check if admin user exists
            result = await db.execute(select(User).where(User.email == "admin@vertexar.com"))
            admin_user = result.scalar_one_or_none()
            
            if not admin_user:
                admin_user = User(
                    email="admin@vertexar.com",
                    hashed_password=get_password_hash("admin123"),
                    full_name="Vertex AR Admin",
                    role="admin",
                    is_active=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(admin_user)
                await db.flush()
                print("✅ Created admin user")
            else:
                print("✅ Admin user already exists")
            
            # Check if company exists
            result = await db.execute(select(Company).where(Company.slug == "vertex-ar"))
            company = result.scalar_one_or_none()
            
            if not company:
                company = Company(
                    name="Vertex AR",
                    slug="vertex-ar",
                    contact_email="admin@vertexar.com",
                    status=CompanyStatus.ACTIVE,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(company)
                await db.flush()
                print("✅ Created company")
            else:
                print("✅ Company already exists")
            
            # Check if project exists
            result = await db.execute(select(Project).where(Project.name == "Портреты"))
            project = result.scalar_one_or_none()
            
            if not project:
                project = Project(
                    name="Портреты",
                    company_id=company.id,
                    status=ProjectStatus.ACTIVE,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(project)
                await db.flush()
                print("✅ Created project")
            else:
                print("✅ Project already exists")
            
            # Check if AR content exists
            result = await db.execute(select(ARContent).where(ARContent.order_number == "ORDER-001"))
            ar_content = result.scalar_one_or_none()
            
            if not ar_content:
                ar_content = ARContent(
                    company_id=company.id,
                    project_id=project.id,
                    order_number="ORDER-001",
                    customer_name="Иван Петров",
                    customer_phone="+7 (999) 123-45-67",
                    customer_email="ivan@example.com",
                    duration_years=3,
                    status=ArContentStatus.ACTIVE,
                    photo_url="/test_data/valid_test_image.png",
                    video_url="/test_data/test_video.mp4",
                    thumbnail_url="/test_data/valid_test_image.png",
                    qr_code_url="/test_data/qr_code.png",
                    marker_url="/test_data/marker.patt",
                    marker_status="ready",
                    unique_id="test-unique-id-001",
                    views_count=0,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(ar_content)
                await db.flush()
                print("✅ Created AR content")
            else:
                print("✅ AR content already exists")
            
            await db.commit()
            print("✅ Test data created successfully!")
            
            # Print summary
            print("\n📊 Test Data Summary:")
            print(f"   Admin User: {admin_user.email}")
            print(f"   Company: {company.name} (ID: {company.id})")
            print(f"   Project: {project.name} (ID: {project.id})")
            print(f"   AR Content: {ar_content.order_number} (ID: {ar_content.id})")
            
        except Exception as e:
            print(f"❌ Error creating test data: {str(e)}")
            await db.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(create_test_data())