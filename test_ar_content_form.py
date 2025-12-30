#!/usr/bin/env python3
"""
Test script to validate AR Content Form fixes
"""

import asyncio
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.company import Company
from app.models.project import Project
from app.core.config import settings

async def test_ar_content_form_data():
    """Test that companies and projects data is correctly structured for the form"""
    
    print("🔍 Testing AR Content Form data structure...")
    
    # Create database connection
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    try:
        async with async_session() as db:
            # Get companies
            companies_query = select(Company)
            companies_result = await db.execute(companies_query)
            companies = []
            for company in companies_result.scalars().all():
                companies.append({
                    "id": company.id,
                    "name": company.name,
                    "contact_email": company.contact_email,
                    "status": company.status,
                    "created_at": company.created_at,
                    "updated_at": company.updated_at
                })
            
            # Get projects
            projects_query = select(Project)
            projects_result = await db.execute(projects_query)
            projects = []
            for project in projects_result.scalars().all():
                projects.append({
                    "id": project.id,
                    "name": project.name,
                    "company_id": project.company_id,
                    "status": project.status,
                    "created_at": project.created_at,
                    "updated_at": project.updated_at
                })
            
            print(f"✅ Found {len(companies)} companies")
            print(f"✅ Found {len(projects)} projects")
            
            # Test data structure
            if companies:
                print(f"📋 Sample company: {companies[0]}")
                print(f"🔍 Company ID type: {type(companies[0]['id'])}")
            
            if projects:
                print(f"📋 Sample project: {projects[0]}")
                print(f"🔍 Project ID type: {type(projects[0]['id'])}")
                print(f"🔍 Project company_id type: {type(projects[0]['company_id'])}")
            
            # Test filtering logic (simulate JavaScript filtering)
            for company in companies:
                company_id_str = str(company['id'])
                company_id_int = int(company['id']) if str(company['id']).isdigit() else company['id']
                
                matching_projects = []
                for project in projects:
                    project_company_id_str = str(project['company_id'])
                    project_company_id_int = int(project['company_id']) if str(project['company_id']).isdigit() else project['company_id']
                    
                    if (project_company_id_str == company_id_str or 
                        project_company_id_int == company_id_int or
                        project_company_id_int == company_id_str or
                        project_company_id_str == company_id_int):
                        matching_projects.append(project)
                
                print(f"🏢 Company '{company['name']}' (ID: {company['id']}) has {len(matching_projects)} projects:")
                for project in matching_projects:
                    print(f"   - {project['name']} (company_id: {project['company_id']})")
            
            # Create JavaScript-compatible data
            companies_js = [
                {
                    "id": company.get("id"),
                    "name": company.get("name"),
                    "status": company.get("status"),
                    "contact_email": company.get("contact_email"),
                    "created_at": (company.get("created_at").isoformat() if company.get("created_at") and hasattr(company.get("created_at"), "isoformat")
                                  else str(company.get("created_at")) if company.get("created_at") else None),
                    "updated_at": (company.get("updated_at").isoformat() if company.get("updated_at") and hasattr(company.get("updated_at"), "isoformat")
                                  else str(company.get("updated_at")) if company.get("updated_at") else None),
                }
                for company in companies
            ]
            
            projects_js = [
                {
                    "id": project.get("id"),
                    "name": project.get("name"),
                    "company_id": project.get("company_id"),
                    "status": project.get("status"),
                    "description": project.get("description"),
                    "created_at": (project.get("created_at").isoformat() if project.get("created_at") and hasattr(project.get("created_at"), "isoformat")
                                  else str(project.get("created_at")) if project.get("created_at") else None),
                    "updated_at": (project.get("updated_at").isoformat() if project.get("updated_at") and hasattr(project.get("updated_at"), "isoformat")
                                  else str(project.get("updated_at")) if project.get("updated_at") else None),
                }
                for project in projects
            ]
            
            print(f"🌐 JavaScript-compatible data created:")
            print(f"   Companies: {len(companies_js)} items")
            print(f"   Projects: {len(projects_js)} items")
            
            # Save test data for manual inspection
            test_data = {
                "companies": companies_js,
                "projects": projects_js
            }
            
            with open('/tmp/ar_content_form_test_data.json', 'w') as f:
                json.dump(test_data, f, indent=2, default=str)
            
            print(f"💾 Test data saved to /tmp/ar_content_form_test_data.json")
            
            return True
            
    except Exception as e:
        print(f"❌ Error testing form data: {e}")
        return False
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_ar_content_form_data())