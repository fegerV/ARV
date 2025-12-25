#!/usr/bin/env python3
"""
Создание базы данных SQLite для тестов
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import engine, Base
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_tables():
    """Создание всех таблиц в базе данных"""
    logger.info(f"Создание таблиц в базе данных: {settings.DATABASE_URL}")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("✅ Таблицы успешно созданы")

async def main():
    """Основная функция"""
    try:
        await create_tables()
        print("🎉 База данных успешно создана!")
        print("📋 Теперь можно запускать:")
        print("   python scripts/test_admin_functionality.py")
    except Exception as e:
        logger.error(f"❌ Ошибка при создании базы данных: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
