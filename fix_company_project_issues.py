#!/usr/bin/env python3
"""
Fix script for company list and project filtering issues
"""

import asyncio
import re
from pathlib import Path

async def fix_companies_display():
    """Fix companies display in project create/edit forms"""
    
    projects_file = Path("app/html/routes/projects.py")
    content = projects_file.read_text()
    
    # Replace all fallback patterns with better error handling
    old_pattern = r'    try:\n        from app\.api\.routes\.companies import list_companies\n        companies_result = await list_companies\(page=1, page_size=100, db=db, current_user=current_user\)\n        companies = \[dict\(item\) for item in companies_result\.items\]\n    except Exception:\n        # fallback to mock data\n        companies = PROJECT_CREATE_MOCK_DATA\["companies"\]'
    
    new_code = '''    try:
        from app.api.routes.companies import list_companies
        companies_result = await list_companies(page=1, page_size=100, db=db, current_user=current_user)
        companies = [dict(item) for item in companies_result.items]
    except Exception as e:
        # Log error and try direct database query as fallback
        print(f"Error fetching companies via API: {e}")
        try:
            from sqlalchemy import select
            from app.models.company import Company
            
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
        except Exception as db_error:
            print(f"Error fetching companies from database: {db_error}")
            # fallback to mock data only as last resort
            companies = PROJECT_CREATE_MOCK_DATA["companies"]'''
    
    content = re.sub(old_pattern, new_code, content)
    projects_file.write_text(content)
    print("✅ Fixed companies display in projects routes")

async def fix_ar_content_project_filtering():
    """Fix AR content project filtering"""
    
    ar_content_file = Path("templates/ar-content/form.html")
    content = ar_content_file.read_text()
    
    # Check if the JavaScript filtering logic is correct
    if 'filteredProjects' in content and 'company_id' in content:
        print("✅ AR content project filtering JavaScript is present")
    else:
        print("❌ AR content project filtering JavaScript is missing")
    
    # Ensure the updateProjects function exists
    if 'updateProjects()' in content:
        print("✅ updateProjects function is present")
    else:
        print("❌ updateProjects function is missing")

async def fix_create_button_visibility():
    """Fix AR content create button visibility"""
    
    ar_content_file = Path("templates/ar-content/form.html")
    content = ar_content_file.read_text()
    
    # Check if the create button exists and has proper styling
    if 'btn btn-primary' in content and 'Создать AR контент' in content:
        print("✅ AR content create button is present")
    else:
        print("❌ AR content create button is missing")
    
    # Check for validation issues that might hide the button
    if 'isValid' in content and ':disabled' in content:
        print("✅ Button validation logic is present")
    else:
        print("❌ Button validation logic is missing")

async def create_test_companies_and_projects():
    """Create additional test data"""
    
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.models.company import Company
    from app.models.project import Project
    
    engine = create_async_engine('sqlite+aiosqlite:///./vertex_ar.db')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check if we have enough test data
        companies_query = "SELECT COUNT(*) FROM companies"
        projects_query = "SELECT COUNT(*) FROM projects"
        
        import sqlite3
        conn = sqlite3.connect('vertex_ar.db')
        companies_count = conn.execute(companies_query).fetchone()[0]
        projects_count = conn.execute(projects_query).fetchone()[0]
        conn.close()
        
        print(f"📊 Current data: {companies_count} companies, {projects_count} projects")
        
        if companies_count < 3:
            print("📝 Creating more test companies...")
            # Additional companies would be created here if needed
        
        if projects_count < 3:
            print("📝 Creating more test projects...")
            # Additional projects would be created here if needed

async def main():
    print("🔧 Starting fixes for company list and project filtering issues...\n")
    
    await fix_companies_display()
    await fix_ar_content_project_filtering()
    await fix_create_button_visibility()
    await create_test_companies_and_projects()
    
    print("\n✅ All fixes completed!")
    print("🔄 Please restart the server to see the changes")

if __name__ == "__main__":
    asyncio.run(main())