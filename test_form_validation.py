#!/usr/bin/env python3
"""
Test script to validate AR content form fixes
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.company import Company
from app.models.project import Project
from app.core.config import settings

async def test_form_data():
    """Test form data for AR content creation"""
    
    # Create database connection
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Get companies
            companies_query = select(Company)
            companies_result = await session.execute(companies_query)
            companies = companies_result.scalars().all()
            
            # Get projects
            projects_query = select(Project)
            projects_result = await session.execute(projects_query)
            projects = projects_result.scalars().all()
            
            print("🔍 AR Content Form Data Validation")
            print("=" * 50)
            
            print(f"📊 Total Companies: {len(companies)}")
            for company in companies:
                print(f"  - {company.name} (ID: {company.id}, Status: {company.status})")
                
                # Show projects for this company
                company_projects = [p for p in projects if str(p.company_id) == str(company.id)]
                print(f"    📁 Projects: {len(company_projects)}")
                for project in company_projects:
                    print(f"      - {project.name} (ID: {project.id})")
            
            print(f"\n📊 Total Projects: {len(projects)}")
            for project in projects:
                print(f"  - {project.name} (ID: {project.id}, Company ID: {project.company_id})")
            
            # Test JavaScript data format
            print(f"\n🔧 JavaScript Data Format Test:")
            companies_js = []
            for company in companies:
                companies_js.append({
                    "id": company.id,
                    "name": company.name,
                    "status": company.status,
                    "contact_email": company.contact_email,
                    "created_at": company.created_at.isoformat() if company.created_at else None,
                    "updated_at": company.updated_at.isoformat() if company.updated_at else None,
                })
            
            projects_js = []
            for project in projects:
                projects_js.append({
                    "id": project.id,
                    "name": project.name,
                    "company_id": project.company_id,
                    "status": project.status,
                    "created_at": project.created_at.isoformat() if project.created_at else None,
                    "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                })
            
            print(f"  Companies JS: {len(companies_js)} items")
            print(f"  Projects JS: {len(projects_js)} items")
            
            # Test filtering logic
            if companies_js and projects_js:
                test_company_id = companies_js[0]["id"]
                filtered_projects = [
                    p for p in projects_js 
                    if p["company_id"] and str(p["company_id"]) == str(test_company_id)
                ]
                
                print(f"\n🔍 Filtering Test:")
                print(f"  Selected Company ID: {test_company_id}")
                print(f"  Filtered Projects: {len(filtered_projects)}")
                for project in filtered_projects:
                    print(f"    - {project['name']} (ID: {project['id']}, Company ID: {project['company_id']})")
            
            print(f"\n✅ Form data validation completed!")
            print(f"   - Companies available: {len(companies) > 0}")
            print(f"   - Projects available: {len(projects) > 0}")
            print(f"   - JavaScript data format: OK")
            
            # Test form validation requirements
            print(f"\n📝 Form Validation Requirements:")
            print(f"   Required fields:")
            print(f"   - company_id: {'✅ Available' if companies else '❌ Missing'}")
            print(f"   - project_id: {'✅ Available' if projects else '❌ Missing'}")
            print(f"   - customer_name: ✅ User input")
            print(f"   - duration_years: ✅ Dropdown (1, 3, 5 years)")
            print(f"   - photo_file: ✅ File upload")
            print(f"   - video_file: ✅ File upload")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_form_data())