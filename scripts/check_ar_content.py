#!/usr/bin/env python3
"""
Скрипт для проверки текущих данных в базе и исправления URL
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.ar_content import ARContent

# Настройка SQLite для тестов
SQLITE_DATABASE_URL = "sqlite+aiosqlite:///./test_vertex_ar.db"

async def check_current_data():
    """Проверка текущих данных в базе"""
    engine = create_async_engine(
        SQLITE_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False}
    )
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Получаем все AR-контент
        result = await session.execute(select(ARContent))
        ar_contents = result.scalars().all()
        
        print("=== Текущий AR-контент в базе ===")
        for ar_content in ar_contents:
            print(f"ID: {ar_content.id}")
            print(f"Название: {ar_content.name}")
            print(f"Заказ: {ar_content.order_number}")
            print(f"Клиент: {ar_content.customer_name}")
            print(f"Уникальный ID: {ar_content.unique_id}")
            print(f"Статус: {ar_content.status}")
            print(f"Проект ID: {ar_content.project_id}")
            print(f"Компания ID: {ar_content.company_id}")
            print("---")
        
        if not ar_contents:
            print("AR-контент не найден")
        else:
            print(f"Всего AR-контента: {len(ar_contents)}")
            print(f"Первый доступный ID: {ar_contents[0].id}")
            print(f"URL для доступа: http://localhost:8000/ar-content/{ar_contents[0].id}")

if __name__ == "__main__":
    asyncio.run(check_current_data())