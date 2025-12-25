#!/usr/bin/env python3
"""
Скрипт для тестирования AR контент страницы
"""

import os
import sys
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

# Устанавливаем переменные окружения для SQLite
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_vertex_ar.db"
os.environ["DEBUG"] = "true"
os.environ["ADMIN_EMAIL"] = "admin@vertexar.com"
os.environ["ADMIN_DEFAULT_PASSWORD"] = "admin123"
os.environ["SECRET_KEY"] = "test-secret-key-for-development"
os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://localhost:8000"
os.environ["MEDIA_ROOT"] = "./storage/content"
os.environ["STORAGE_BASE_PATH"] = "./storage/content"
os.environ["LOCAL_STORAGE_PATH"] = "./storage/content"
os.environ["TEMPLATES_DIR"] = "./templates"
os.environ["STATIC_DIR"] = "./static"

import asyncio
from app.html.routes.ar_content import ar_content_detail
from app.models.user import User
from app.core.database import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

async def test_ar_content_page():
    """Тестирование страницы AR контента"""
    print("🧪 Тестирование страницы AR контента...")
    
    # Создаем фейковый request
    class MockRequest:
        def __init__(self):
            self.query_params = {}
    
    # Создаем фейкового пользователя
    class MockUser:
        def __init__(self):
            self.id = 1
            self.email = "admin@vertexar.com"
            self.full_name = "Vertex AR Admin"
            self.role = "admin"
            self.is_active = True
    
    async with AsyncSessionLocal() as db:
        try:
            # Вызываем функцию обработчика
            result = await ar_content_detail(
                ar_content_id="1",
                request=MockRequest(),
                current_user=MockUser(),
                db=db
            )
            
            print("✅ Страница AR контента успешно сгенерирована")
            print(f"📄 Тип ответа: {type(result)}")
            print(f"📄 Код статуса: {result.status_code if hasattr(result, 'status_code') else 'N/A'}")
            
            # Проверяем содержимое
            if hasattr(result, 'body'):
                content = result.body.decode('utf-8')
                if 'ORDER-001' in content:
                    print("✅ Данные AR контента найдены в шаблоне")
                if 'Иван Петров' in content:
                    print("✅ Имя клиента найдено в шаблоне")
                if 'video1.mp4' in content:
                    print("✅ Активное видео найдено в шаблоне")
                
                print(f"📊 Размер контента: {len(content)} символов")
            
        except Exception as e:
            print(f"❌ Ошибка при генерации страницы: {e}")
            import traceback
            traceback.print_exc()
            
            # Debug: let's see what's in ar_content before template rendering
            if 'ar_content' in locals():
                print("\n🔍 Debug - ar_content keys:", list(ar_content.keys()) if isinstance(ar_content, dict) else "Not a dict")
                for key, value in ar_content.items() if isinstance(ar_content, dict) else []:
                    if hasattr(value, 'isoformat'):
                        print(f"⚠️  {key}: datetime object detected")
                    elif isinstance(value, dict):
                        for subkey, subvalue in value.items():
                            if hasattr(subvalue, 'isoformat'):
                                print(f"⚠️  {key}.{subkey}: datetime object detected")

if __name__ == "__main__":
    asyncio.run(test_ar_content_page())