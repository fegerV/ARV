#!/usr/bin/env python3
"""
Script to create test project for AR content form testing
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.company import Company
from app.models.project import Project
from app.core.config import settings
from datetime import datetime

async def create_test_project():
    """Create a test project for AR content form testing"""
    
    # Create database connection
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Get the existing company
            companies_query = select(Company)
            companies_result = await session.execute(companies_query)
            companies = companies_result.scalars().all()
            
            if not companies:
                print("❌ No companies found. Please create a company first.")
                return
            
            company = companies[0]
            print(f"🏢 Using company: {company.name} (ID: {company.id})")
            
            # Create a test project
            test_project = Project(
                name="Портреты",
                company_id=company.id,
                status="active",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            session.add(test_project)
            await session.commit()
            await session.refresh(test_project)
            
            print(f"✅ Created test project: {test_project.name} (ID: {test_project.id})")
            print(f"   Company ID: {test_project.company_id}")
            print(f"   Status: {test_project.status}")
            
            # Verify creation
            projects_query = select(Project)
            projects_result = await session.execute(projects_query)
            projects = projects_result.scalars().all()
            
            print(f"\n📁 Total projects in database: {len(projects)}")
            for project in projects:
                print(f"  - {project.name} (ID: {project.id}, Company ID: {project.company_id})")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(create_test_project())