#!/usr/bin/env python3
"""
Script to test AR Content form data
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

async def test_ar_content_form_data():
    """Test companies and projects data for AR content form"""
    
    # Create database connection
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Test companies
            print("🏢 Testing companies...")
            companies_query = select(Company)
            companies_result = await session.execute(companies_query)
            companies = companies_result.scalars().all()
            
            print(f"Found {len(companies)} companies:")
            for company in companies:
                print(f"  - {company.name} (ID: {company.id}, Status: {company.status})")
            
            # Test projects
            print("\n📁 Testing projects...")
            projects_query = select(Project)
            projects_result = await session.execute(projects_query)
            projects = projects_result.scalars().all()
            
            print(f"Found {len(projects)} projects:")
            for project in projects:
                print(f"  - {project.name} (ID: {project.id}, Company ID: {project.company_id}, Status: {project.status})")
            
            # Test project filtering
            print("\n🔍 Testing project filtering...")
            if companies:
                first_company = companies[0]
                company_projects = [p for p in projects if str(p.company_id) == str(first_company.id)]
                print(f"Projects for company '{first_company.name}' (ID: {first_company.id}):")
                for project in company_projects:
                    print(f"  - {project.name} (ID: {project.id})")
                
                if not company_projects:
                    print("  ⚠️  No projects found for this company!")
            
            # Create test data if needed
            if not companies:
                print("\n⚠️  No companies found. Creating test data...")
                # This would require creating test companies and projects
                
            if not projects:
                print("\n⚠️  No projects found. Creating test data...")
                # This would require creating test companies and projects
            
            print("\n✅ Test completed successfully!")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ar_content_form_data())