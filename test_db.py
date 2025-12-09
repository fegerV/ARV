import asyncio
import asyncpg

async def test_db_connection():
    """Test database connection"""
    try:
        # Try to connect to the database
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='vertex_ar',
            password='password',
            database='vertex_ar'
        )
        
        # Execute a simple query
        result = await conn.fetchval('SELECT 1')
        print(f"Database connection successful. Query result: {result}")
        
        # Close the connection
        await conn.close()
        
    except Exception as e:
        print(f"Database connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_db_connection())