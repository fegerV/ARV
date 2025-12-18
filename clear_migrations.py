import asyncio
from app.core.database import engine
from sqlalchemy import text

async def clear_migration_table():
    try:
        async with engine.connect() as conn:
            await conn.execute(text('DROP TABLE IF EXISTS alembic_version'))
            await conn.commit()
            print("Таблица alembic_version успешно удалена")
    except Exception as e:
        print(f"Ошибка при удалении таблицы alembic_version: {e}")

if __name__ == "__main__":
    asyncio.run(clear_migration_table())