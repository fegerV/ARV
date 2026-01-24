#!/usr/bin/env python3
"""
Start test server for admin interface testing.
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

async def setup_test_data():
    """Setup test database and admin user."""
    from app.core.database import init_db_sync, AsyncSessionLocal
    from app.models.user import User
    from app.core.security import get_password_hash
    from app.models.company import Company
    from app.models.project import Project
    from app.models.ar_content import ARContent
    from sqlalchemy import select
    
    print("🔧 Setting up test database...")
    
    # Initialize database
    init_db_sync()
    
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
        
        # Create test project
        result = await db.execute(
            select(Project).where(Project.name == "Тестовый проект")
        )
        project = result.scalar_one_or_none()
        
        if not project:
            project = Project(
                name="Тестовый проект",
                slug="test-project",
                company_id=company.id,
                status="active"
            )
            db.add(project)
            await db.commit()
            await db.refresh(project)
            print("✅ Created test project")
        
        # Create test AR content
        result = await db.execute(
            select(ARContent).where(ARContent.order_number == "TEST-001")
        )
        ar_content = result.scalar_one_or_none()
        
        if not ar_content:
            ar_content = ARContent(
                order_number="TEST-001",
                customer_name="Тестовый клиент",
                customer_phone="+7 (999) 123-45-67",
                customer_email="test@example.com",
                company_id=company.id,
                project_id=project.id,
                status="ready",
                unique_id="test-unique-id-12345"
            )
            db.add(ar_content)
            await db.commit()
            print("✅ Created test AR content")
    
    print("✅ Test data setup completed!")

def main():
    """Main function to start the server."""
    print("🚀 Starting test server for admin interface...")
    
    # Setup test data
    asyncio.run(setup_test_data())
    
    print("\n📝 Server Information:")
    print("🌐 URL: http://localhost:8000")
    print("🔐 Admin Login: http://localhost:8000/admin/login")
    print("👤 Email: admin@vertexar.com")
    print("🔑 Password: admin123")
    print("\n🎯 Testing Checklist:")
    print("1. Login page loads with proper styles")
    print("2. Theme toggle works (🌙/☀️)")
    print("3. Dark mode applies correctly")
    print("4. Dashboard shows metrics")
    print("5. No white text on white background")
    print("\n⚠️  Press Ctrl+C to stop the server")
    
    # Start the server
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
