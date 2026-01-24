#!/usr/bin/env python3
"""
Create test data for AR Content Form testing
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.company import Company
from app.models.project import Project
from app.core.config import settings

async def create_test_project():
    """Create a test project for the existing company"""
    
    print("🔧 Creating test project...")
    
    # Create database connection
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    try:
        async with async_session() as db:
            # Get the existing company
            companies_query = select(Company).where(Company.name == "Vertex AR")
            companies_result = await db.execute(companies_query)
            company = companies_result.scalar_one_or_none()
            
            if not company:
                print("❌ No company found")
                return False
            
            print(f"✅ Found company: {company.name} (ID: {company.id})")
            
            # Check if project already exists
            existing_project_query = select(Project).where(Project.name == "Портреты")
            existing_result = await db.execute(existing_project_query)
            existing_project = existing_result.scalar_one_or_none()
            
            if existing_project:
                print(f"✅ Project already exists: {existing_project.name}")
                return True
            
            # Create new project
            new_project = Project(
                name="Портреты",
                company_id=company.id,
                status="active"
            )
            
            db.add(new_project)
            await db.commit()
            await db.refresh(new_project)
            
            print(f"✅ Created project: {new_project.name} (ID: {new_project.id})")
            print(f"   Company ID: {new_project.company_id}")
            print(f"   Status: {new_project.status}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error creating test project: {e}")
        return False
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_test_project())
