import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import get_settings

settings = get_settings()
DATABASE_URL = settings.DATABASE_URL

async def check_seed_data():
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.connect() as conn:
        # Check admin user
        result = await conn.execute(
            text("SELECT id, email, role FROM users WHERE email = :email"),
            {"email": "admin@vertex.local"}
        )
        admin_user = result.fetchone()
        
        print("Admin user:")
        if admin_user:
            print(f" ID: {admin_user[0]}")
            print(f"  Email: {admin_user[1]}")
            print(f"  Role: {admin_user[2]}")
        else:
            print("  Not found")
        
        # Check company
        result = await conn.execute(
            text("SELECT id, name, contact_email, status FROM companies WHERE name = :name"),
            {"name": "Vertex AR"}
        )
        company = result.fetchone()
        
        print("\nCompany:")
        if company:
            print(f"  ID: {company[0]}")
            print(f"  Name: {company[1]}")
            print(f"  Contact Email: {company[2]}")
            print(f"  Status: {company[3]}")
        else:
            print("  Not found")
        
        # Let's also check all companies to see what was actually inserted
        print("\nAll companies in DB:")
        result = await conn.execute(text("SELECT id, name, contact_email FROM companies"))
        all_companies = result.fetchall()
        for comp in all_companies:
            print(f"  ID: {comp[0]}, Name: {comp[1]}, Contact Email: {comp[2]}")
        
        # And all users
        print("\nAll users in DB:")
        result = await conn.execute(text("SELECT id, email, full_name FROM users"))
        all_users = result.fetchall()
        for user in all_users:
            print(f"  ID: {user[0]}, Email: {user[1]}, Full Name: {user[2]}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_seed_data())