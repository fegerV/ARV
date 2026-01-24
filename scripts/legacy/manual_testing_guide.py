#!/usr/bin/env python3
"""
Manual testing checklist for AR content creation workflow
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent))

# Устанавливаем переменные окружения для локальной среды
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_vertex_ar.db"
os.environ["ADMIN_EMAIL"] = "admin@vertexar.com"
os.environ["ADMIN_DEFAULT_PASSWORD"] = "admin123"
os.environ["DEBUG"] = "true"
os.environ["ENVIRONMENT"] = "development"
os.environ["MEDIA_ROOT"] = "./tmp/storage"
os.environ["STORAGE_BASE_PATH"] = "./tmp/storage"

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.company import Company
from app.models.project import Project
from app.models.ar_content import ARContent
from app.models.video import Video
from app.models.user import User
from sqlalchemy import select

def print_checklist():
    """Print the manual testing checklist"""
    print("🔍 РУКОВОДСТВО ПО РУЧНОМУ ТЕСТИРОВАНИЮ АДМИН-ПАНЕЛИ VERTEX AR")
    print("=" * 70)
    
    print("\n📋 ИНФОРМАЦИЯ О СЕРВЕРЕ:")
    print("   • Сервер должен быть запущен на http://localhost:8000")
    print("   • Админ-панель: http://localhost:8000/admin")
    print("   • API документация: http://localhost:8000/docs")
    
    print("\n👤 ДАННЫЕ ДЛЯ ВХОДА:")
    print("   • Email: admin@vertexar.com")
    print("   • Пароль: admin123")
    
    print("\n🎯 ЧЕК-ЛИСТ ТЕСТИРОВАНИЯ:")
    print("=" * 50)
    
    print("\n1. ✅ ВХОД В АДМИН-ПАНЕЛЬ")
    print("   [ ] Зайти в http://localhost:8000/admin")
    print("   [ ] Ввести admin@vertexar.com / admin123")
    print("   [ ] Убедиться что вход успешен и открывается дашборд")
    
    print("\n2. ✅ ПРОВЕРКА ПРОЕКТА 'ПОРТРЕТЫ'")
    print("   [ ] Перейти в раздел /projects")
    print("   [ ] Найти проект 'Портреты'")
    print("   [ ] Проверить что проект отображается корректно")
    print("   [ ] Убедиться что статус проекта 'active'")
    
    print("\n3. ✅ СОЗДАНИЕ НОВОГО AR-КОНТЕНТА")
    print("   [ ] Нажать 'Создать AR-контент' в проекте 'Портреты'")
    print("   [ ] Заполнить поля заказчика:")
    print("       - Имя заказчика: Тестовый клиент")
    print("       - Телефон: +7 (999) 888-76-54")
    print("       - Email: test@example.com")
    print("       - Номер заказа: ORDER-TEST-001")
    print("   [ ] Установить длительность: 3 года")
    print("   [ ] Сохранить AR-контент")
    
    print("\n4. ✅ ЗАГРУЗКА ФАЙЛОВ")
    print("   [ ] Загрузить фото (использовать test_data/valid_test_image.png)")
    print("   [ ] Загрузить видео (использовать test_data/test_video.mp4)")
    print("   [ ] Проверить что файлы загружаются корректно")
    print("   [ ] Убедиться что создаются превью")
    
    print("\n5. ✅ ГЕНЕРАЦИЯ МАРКЕРОВ")
    print("   [ ] Нажать 'Сгенерировать маркеры'")
    print("   [ ] Проверить что процесс запускается")
    print("   [ ] Убедиться что статус маркера обновляется")
    print("   [ ] Проверить что создается .mind файл")
    
    print("\n6. ✅ УПРАВЛЕНИЕ ВИДЕО")
    print("   [ ] Проверить отображение загруженного видео")
    print("   [ ] Установить видео как 'активное'")
    print("   [ ] Загрузить второе видео")
    print("   [ ] Переключить активное видео между ними")
    print("   [ ] Проверить что только одно видео может быть активным")
    
    print("\n7. ✅ ЛАЙТБОКС ДЛЯ ПРЕВЬЮ")
    print("   [ ] Нажать на превью фото")
    print("   [ ] Проверить что открывается лайтбокс")
    print("   [ ] Убедиться что изображение отображается в полном размере")
    print("   [ ] Проверить что лайтбокс закрывается по клику вне области")
    
    print("\n8. ✅ 3-ЛЕТНЕЕ РАЗМЕЩЕНИЕ ВИДЕО")
    print("   [ ] Проверить что дата окончания подписки установлена на 3 года")
    print("   [ ] Убедиться что подписка отображается в админке")
    print("   [ ] Проверить что видео доступно в AR viewer")
    
    print("\n9. ✅ ПРОВЕРКА ССЫЛОК И QR-КОДОВ")
    print("   [ ] Проверить что создана уникальная ссылка")
    print("   [ ] Убедиться что ссылка работает: /view/{unique_id}")
    print("   [ ] Проверить что QR-код генерируется")
    print("   [ ] Убедиться что QR-код ведет на правильную страницу")
    
    print("\n10. ✅ ПРОВЕРКА AR VIEWER")
    print("    [ ] Перейти по уникальной ссылке AR-контента")
    print("    [ ] Проверить что открывается AR viewer")
    print("    [ ] Убедиться что отображается загруженное фото")
    print("    [ ] Проверить что видео воспроизводится при наведении")
    
    print("\n📊 ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ:")
    print("   • Все формы должны сохранять данные без ошибок")
    print("   • Файлы должны загружаться и обрабатываться корректно")
    print("   • Маркеры должны генерироваться без ошибок")
    print("   • Лайтбокс должен работать плавно")
    print("   • Переключение между видео должно работать")
    print("   • AR viewer должен отображать контент")
    
    print("\n🐛 ВОЗМОЖНЫЕ ПРОБЛЕМЫ И РЕШЕНИЯ:")
    print("   • Ошибка 500: Проверить логи сервера")
    print("   • Файлы не загружаются: Проверить права доступа к tmp/storage")
    print("   • Маркеры не генерируются: Проверить установку OpenCV")
    print("   • Лайтбокс не работает: Проверить JavaScript в браузере")
    
    print("\n📝 ЗАМЕЧАНИЯ:")
    print("   • Записывайте все найденные проблемы")
    print("   • Делайте скриншоты ошибок")
    print("   • Проверьте работоспособность на разных браузерах")
    
    print("\n" + "=" * 70)
    print("✅ ГОТОВО К ТЕСТИРОВАНИЮ!")

async def verify_test_data():
    """Verify that test data exists"""
    print("\n🔍 ПРОВЕРКА ТЕСТОВЫХ ДАННЫХ...")
    
    engine = create_async_engine(
        "sqlite+aiosqlite:///./test_vertex_ar.db",
        echo=False,
        connect_args={"check_same_thread": False}
    )
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        try:
            # Проверяем компании
            companies_result = await session.execute(select(Company))
            companies = companies_result.scalars().all()
            print(f"   📊 Компании: {len(companies)}")
            for company in companies:
                print(f"      - {company.name} ({company.slug})")
            
            # Проверяем проекты
            projects_result = await session.execute(select(Project))
            projects = projects_result.scalars().all()
            print(f"   📊 Проекты: {len(projects)}")
            for project in projects:
                print(f"      - {project.name} (статус: {project.status})")
            
            # Проверяем AR-контент
            ar_contents_result = await session.execute(select(ARContent))
            ar_contents = ar_contents_result.scalars().all()
            print(f"   📊 AR-контент: {len(ar_contents)}")
            for content in ar_contents:
                print(f"      - {content.order_number} - {content.customer_name}")
                print(f"        Ссылка: /view/{content.unique_id}")
            
            # Проверяем видео
            videos_result = await session.execute(select(Video))
            videos = videos_result.scalars().all()
            print(f"   📊 Видео: {len(videos)}")
            for video in videos:
                status = "🟢 Активное" if video.is_active else "⚪ Неактивное"
                print(f"      {status} {video.filename}")
            
            # Проверяем файлы тестовых данных
            print(f"\n   📁 Проверка тестовых файлов:")
            test_image = Path("test_data/valid_test_image.png")
            test_video = Path("test_data/test_video.mp4")
            
            if test_image.exists():
                print(f"      ✅ {test_image}")
            else:
                print(f"      ❌ {test_image} - отсутствует")
            
            if test_video.exists():
                print(f"      ✅ {test_video}")
            else:
                print(f"      ❌ {test_video} - отсутствует")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Ошибка при проверке данных: {e}")
            return False

def main():
    """Main function"""
    print_checklist()
    
    # Проверяем тестовые данные
    success = asyncio.run(verify_test_data())
    
    if success:
        print("\n✅ Система готова к ручному тестированию!")
        print("\n🚀 ЗАПУСК СЕРВЕРА:")
        print("   DATABASE_URL=\"sqlite+aiosqlite:///./test_vertex_ar.db\" \\")
        print("   ADMIN_EMAIL=\"admin@vertexar.com\" \\")
        print("   ADMIN_DEFAULT_PASSWORD=\"admin123\" \\")
        print("   DEBUG=\"true\" ENVIRONMENT=\"development\" \\")
        print("   MEDIA_ROOT=\"./tmp/storage\" STORAGE_BASE_PATH=\"./tmp/storage\" \\")
        print("   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000")
    else:
        print("\n❌ Система не готова к тестированию. Проверьте ошибки выше.")

if __name__ == "__main__":
    main()
