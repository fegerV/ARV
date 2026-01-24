#!/usr/bin/env python3
"""
Create admin user for testing.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment variables for testing
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_vertex_ar.db")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-admin-testing")

async def create_admin():
    """Create admin user and test data."""
    from app.core.database import AsyncSessionLocal
    from app.models.user import User
    from app.core.security import get_password_hash
    from app.models.company import Company
    from app.models.project import Project
    from app.models.ar_content import ARContent
    from sqlalchemy import select
    
    print("🔧 Creating admin user and test data...")
    
    async with AsyncSessionLocal() as db:
        # Create admin user
        result = await db.execute(
            select(User).where(User.email == "admin@vertexar.com")
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            admin = User(
                email="admin@vertexar.com",
                hashed_password=get_password_hash("admin123"),
                full_name="Administrator",
                is_active=True,
                role="admin"
            )
            db.add(admin)
            await db.commit()
            print("✅ Created admin user")
        else:
            print("✅ Admin user already exists")
        
        # Create test company
        result = await db.execute(
            select(Company).where(Company.slug == "vertex-ar")
        )
        company = result.scalar_one_or_none()
        
        if not company:
            company = Company(
                name="Vertex AR",
                slug="vertex-ar",
                contact_email="admin@vertexar.com",
                status="active"
            )
            db.add(company)
            await db.commit()
            await db.refresh(company)
            print("✅ Created test company")
        else:
            print("✅ Test company already exists")
            await db.refresh(company)
        
        # Create test project "Портреты"
        result = await db.execute(
            select(Project).where((Project.name == "Портреты") & (Project.company_id == company.id))
        )
        project = result.scalar_one_or_none()
        
        if not project:
            project = Project(
                name="Портреты",
                slug="portrets",  # URL-friendly slug
                company_id=company.id,
                status="active"
            )
            db.add(project)
            await db.commit()
            await db.refresh(project)
            print("✅ Created project 'Портреты'")
        else:
            print("✅ Project 'Портреты' already exists")
            await db.refresh(project)
    
    print("✅ Setup completed!")
    print("\n📝 Login Information:")
    print("🌐 URL: http://localhost:8000/admin/login")
    print("👤 Email: admin@vertexar.com")
    print("🔑 Password: admin123")

if __name__ == "__main__":
    asyncio.run(create_admin())
