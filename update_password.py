import asyncio
import asyncpg

async def update_password():
    # Connect to the database
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='vertex_ar',
        password='StrongPassword123',
        database='vertex_ar'
    )
    
    # Hash a simple password
    import bcrypt
    password = 'pass123'
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    # Update the user's password
    await conn.execute(
        "UPDATE users SET hashed_password = $1 WHERE email = $2",
        hashed.decode('utf-8'),
        'admin@vertexar.com'
    )
    
    print(f"Updated password hash: {hashed.decode('utf-8')} with password 'pass123'")
    
    # Verify the update
    row = await conn.fetchrow(
        "SELECT hashed_password FROM users WHERE email = $1",
        'admin@vertexar.com'
    )
    
    print(f"Retrieved password hash: {row['hashed_password']}")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(update_password())