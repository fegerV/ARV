#!/usr/bin/env python3
"""Тестирование провайдеров хранилища"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import AsyncSessionLocal
from app.models.storage import StorageConnection
from app.services.storage.factory import get_provider


async def test_storage_providers():
    """Тестирование провайдеров хранилища"""
    async with AsyncSessionLocal() as db:
        # Получаем все подключения к хранилищу
        connections = await db.execute("SELECT * FROM storage_connections")
        connections = connections.fetchall()
        
        print(f"Найдено {len(connections)} подключений к хранилищу:")
        
        for conn in connections:
            print(f"\n--- Тестирование подключения {conn.id} ({conn.provider}) ---")
            print(f"Название: {conn.name}")
            print(f"Путь/endpoint: {conn.base_path or conn.endpoint}")
            
            try:
                # Получаем провайдер
                provider = get_provider(conn)
                print(f"Провайдер успешно создан: {type(provider).__name__}")
                
                # Тестируем создание папки
                result = await provider.create_folder("test_folder")
                print(f"Создание папки: {'Успешно' if result.get('success') else 'Ошибка'}")
                if not result.get('success'):
                    print(f"  Ошибка: {result.get('error')}")
                    
            except Exception as e:
                print(f"Ошибка при создании провайдера: {e}")


if __name__ == "__main__":
    asyncio.run(test_storage_providers())