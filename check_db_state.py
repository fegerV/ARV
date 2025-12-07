import asyncio
import asyncpg
from app.core.config import settings

async def check_db():
    try:
        # Connect to database
        conn = await asyncpg.connect(settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://'))
        
        # Get all tables
        tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        tables = await conn.fetch(tables_query)
        print(f'Current tables: {[table["table_name"] for table in tables]}')
        
        # Check userrole enum
        enum_query = """
            SELECT enumlabel 
            FROM pg_enum 
            WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'userrole')
            ORDER BY enumsortorder
        """
        try:
            enum_values = await conn.fetch(enum_query)
            print(f'UserRole enum values: {[val["enumlabel"] for val in enum_values]}')
        except Exception as e:
            print(f'Error checking enum: {e}')
        
        # Check storage_connections columns
        columns_query = """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'storage_connections'
            ORDER BY ordinal_position
        """
        columns = await conn.fetch(columns_query)
        print(f'\nStorage connections columns:')
        for col in columns:
            print(f'  {col["column_name"]}: {col["data_type"]} (nullable: {col["is_nullable"]})')
        
        # Check video_rotation_schedules columns
        columns_query = """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'video_rotation_schedules'
            ORDER BY ordinal_position
        """
        columns = await conn.fetch(columns_query)
        print(f'\nVideo rotation schedules columns:')
        for col in columns:
            print(f'  {col["column_name"]}: {col["data_type"]} (nullable: {col["is_nullable"]})')
        
        await conn.close()
        
    except Exception as e:
        print(f'Database connection error: {e}')

if __name__ == '__main__':
    asyncio.run(check_db())