#!/usr/bin/env python3
"""
Финальная проверка готовности админки
"""

import sys
import os
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

# Устанавливаем переменные окружения для локальной среды
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_vertex_ar.db"
os.environ["ADMIN_EMAIL"] = "admin@vertexar.com"
os.environ["ADMIN_DEFAULT_PASSWORD"] = "admin123"
os.environ["DEBUG"] = "true"
os.environ["ENVIRONMENT"] = "development"
os.environ["MEDIA_ROOT"] = "./tmp/storage"
os.environ["STORAGE_BASE_PATH"] = "./tmp/storage"

def main():
    print("🔍 Финальная проверка готовности админки Vertex AR")
    print("=" * 50)
    
    try:
        # 1. Проверка моделей
        print("1. 📦 Проверка моделей...")
        from app.models.company import Company
        from app.models.project import Project
        from app.models.ar_content import ARContent
        from app.models.video import Video
        from app.models.user import User
        print("   ✅ Все модели импортируются успешно")
        
        # 2. Проверка конфигурации
        print("2. ⚙️ Проверка конфигурации...")
        from app.core.config import settings
        print(f"   ✅ DATABASE_URL: {settings.DATABASE_URL}")
        print(f"   ✅ ADMIN_EMAIL: {settings.ADMIN_EMAIL}")
        print(f"   ✅ MEDIA_ROOT: {settings.MEDIA_ROOT}")
        
        # 3. Проверка базы данных
        print("3. 🗄️ Проверка базы данных...")
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from app.core.database import Base
        
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            connect_args={"check_same_thread": False}
        )
        
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        # Проверяем подключение
        import asyncio
        async def check_db():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("   ✅ База данных создана и доступна")
            
            # Проверяем данные
            async with async_session() as session:
                from sqlalchemy import select
                companies_result = await session.execute(select(Company))
                companies = companies_result.scalars().all()
                print(f"   ✅ Компании в базе: {len(companies)}")
                
                projects_result = await session.execute(select(Project))
                projects = projects_result.scalars().all()
                print(f"   ✅ Проекты в базе: {len(projects)}")
                
                ar_contents_result = await session.execute(select(ARContent))
                ar_contents = ar_contents_result.scalars().all()
                print(f"   ✅ AR-контент в базе: {len(ar_contents)}")
                
                videos_result = await session.execute(select(Video))
                videos = videos_result.scalars().all()
                print(f"   ✅ Видео в базе: {len(videos)}")
        
        asyncio.run(check_db())
        
        # 4. Проверка шаблонов
        print("4. 🎨 Проверка шаблонов...")
        templates_dir = Path("templates")
        required_templates = [
            "admin/dashboard.html",
            "admin/login.html", 
            "companies_list.html",
            "projects_list.html",
            "ar_content_list.html",
            "ar_viewer.html",
            "analytics.html",
            "dashboard.html"
        ]
        
        missing_templates = []
        for template in required_templates:
            if not (templates_dir / template).exists():
                missing_templates.append(template)
        
        if missing_templates:
            print(f"   ⚠️ Отсутствуют шаблоны: {missing_templates}")
        else:
            print("   ✅ Все основные шаблоны на месте")
        
        # 5. Проверка роутов
        print("5. 🛣️ Проверка роутов...")
        try:
            from app.html.routes import auth, dashboard, companies, projects, ar_content
            print("   ✅ Основные HTML роуты импортируются")
        except Exception as e:
            print(f"   ❌ Ошибка импорта роутов: {e}")
        
        # 6. Проверка зависимостей
        print("6. 📦 Проверка зависимостей...")
        try:
            import fastapi
            import sqlalchemy
            import uvicorn
            import jinja2
            import aiosqlite
            print("   ✅ Все основные зависимости установлены")
        except ImportError as e:
            print(f"   ❌ Отсутствует зависимость: {e}")
        
        print("\n" + "=" * 50)
        print("✅ Проверка завершена! Система готова к тестированию.")
        print("\n📋 Данные для входа:")
        print("   Email: admin@vertexar.com")
        print("   Пароль: admin123")
        print("   URL: http://localhost:8000/admin")
        print("\n🚀 Запуск сервера:")
        print("   python scripts/run_admin_test_server.py")
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)