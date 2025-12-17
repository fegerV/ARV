import asyncio
import hashlib
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import get_settings

settings = get_settings()
DATABASE_URL = settings.DATABASE_URL

async def test_admin_login():
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.connect() as conn:
        # Get the admin user we created
        result = await conn.execute(
            text("SELECT id, email, hashed_password FROM users WHERE email = :email"),
            {"email": "admin@vertex.local"}
        )
        admin_user = result.fetchone()
        
        if admin_user:
            print(f"Found admin user: {admin_user[1]}")
            print(f"User ID: {admin_user[0]}")
            
            # Test password verification using the same method as the application
            input_password = "admin123"
            expected_hash = hashlib.sha256(input_password.encode()).hexdigest()
            stored_hash = admin_user[2]
            
            if expected_hash == stored_hash:
                print("SUCCESS: Password verification successful! Admin user is properly set up.")
                print(f"  Expected hash: {expected_hash}")
                print(f"  Stored hash:   {stored_hash}")
            else:
                print("ERROR: Password verification failed!")
                print(f" Expected hash: {expected_hash}")
                print(f"  Stored hash:   {stored_hash}")
        else:
            print("❌ Admin user not found!")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_admin_login())