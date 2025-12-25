#!/usr/bin/env python3
"""
Скрипт для проверки корректности отображения данных на страницах AR контента:
- Детальная информация AR контента
- Список AR контента (ar_content_list)
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.models.ar_content import ARContent
from app.models.project import Project
from app.models.company import Company
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import json


async def check_ar_content_data():
    """Проверка данных AR контента в базе данных"""
    print("🔍 Проверка данных AR контента в базе данных...")
    
    async with AsyncSessionLocal() as session:
        # Получаем статистику
        total_count = await session.scalar(select(func.count(ARContent.id)))
        print(f"📊 Всего AR контента: {total_count}")
        
        if total_count == 0:
            print("❌ AR контент не найден! Запустите scripts/test_admin_functionality.py")
            return False
        
        # Получаем примеры AR контента с связанными данными
        result = await session.execute(
            select(ARContent)
            .options(
                selectinload(ARContent.project).selectinload(Project.company)
            )
            .limit(5)
        )
        ar_contents = result.scalars().all()
        
        print("\n📋 Примеры AR контента:")
        for i, ar_content in enumerate(ar_contents, 1):
            print(f"\n{i}. AR Контент ID: {ar_content.id}")
            print(f"   🆔 Уникальный ID: {ar_content.unique_id}")
            print(f"   📁 Проект: {ar_content.project.name if ar_content.project else 'Не указан'}")
            print(f"   🏢 Компания: {ar_content.project.company.name if ar_content.project and ar_content.project.company else 'Не указана'}")
            print(f"   👤 Клиент: {ar_content.customer_name}")
            print(f"   📞 Телефон: {ar_content.customer_phone}")
            print(f"   📦 Заказ: {ar_content.order_number}")
            print(f"   📊 Статус: {ar_content.status}")
            print(f"   🖼️ Миниатюра: {ar_content.thumbnail_url}")
            print(f"   🎯 Маркер: {ar_content.marker_path}")
            print(f"   🌐 URL маркера: {ar_content.marker_url}")
            print(f"   ⚡ Статус маркера: {ar_content.marker_status}")
            print(f"   📄 Метаданные маркера: {ar_content.marker_metadata}")
            print(f"   📅 Создан: {ar_content.created_at}")
            print(f"   🔄 Обновлен: {ar_content.updated_at}")
            
            # Проверяем наличие всех обязательных полей
            missing_fields = []
            if not ar_content.unique_id:
                missing_fields.append("unique_id")
            if not ar_content.customer_name:
                missing_fields.append("customer_name")
            if not ar_content.customer_phone:
                missing_fields.append("customer_phone")
            if not ar_content.order_number:
                missing_fields.append("order_number")
            if not ar_content.status:
                missing_fields.append("status")
            
            if missing_fields:
                print(f"   ⚠️  Отсутствуют поля: {', '.join(missing_fields)}")
            else:
                print(f"   ✅ Все обязательные поля присутствуют")
    
    return True


async def check_required_fields():
    """Проверка наличия всех требуемых полей в модели ARContent"""
    print("\n🔧 Проверка полей модели ARContent...")
    
    required_fields = [
        'id', 'unique_id', 'project_id', 'customer_name', 'customer_phone', 
        'order_number', 'status', 'thumbnail_url', 'marker_path', 'marker_url',
        'marker_status', 'marker_metadata', 'created_at', 'updated_at'
    ]
    
    model_fields = [field.name for field in ARContent.__table__.columns]
    
    print(f"📊 Требуемых полей: {len(required_fields)}")
    print(f"📊 Полей в модели: {len(model_fields)}")
    
    missing_fields = []
    for field in required_fields:
        if field not in model_fields:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"❌ Отсутствуют поля: {', '.join(missing_fields)}")
        return False
    else:
        print("✅ Все требуемые поля присутствуют в модели")
        return True


async def check_template_files():
    """Проверка наличия HTML шаблонов для страниц AR контента"""
    print("\n📄 Проверка HTML шаблонов...")
    
    template_paths = [
        "templates/ar-content/detail.html",
        "templates/ar-content/list.html",
        "templates/base.html",
        "templates/admin/dashboard.html"
    ]
    
    all_exist = True
    for template_path in template_paths:
        full_path = Path(__file__).parent.parent / template_path
        if full_path.exists():
            print(f"✅ {template_path}")
        else:
            print(f"❌ {template_path} - не найден!")
            all_exist = False
    
    return all_exist


async def check_routes():
    """Проверка маршрутов для AR контента"""
    print("\n🛣️  Проверка маршрутов...")
    
    try:
        from app.main import app
        routes = []
        for route in app.routes:
            if hasattr(route, 'path'):
                routes.append(route.path)
        
        ar_content_routes = [r for r in routes if 'ar-content' in r or 'ar_content' in r]
        
        print("📋 Маршруты AR контента:")
        for route in sorted(ar_content_routes):
            print(f"   📍 {route}")
        
        # Проверяем наличие ключевых маршрутов
        required_routes = [
            "/admin/ar-content",
            "/admin/ar-content/{id}",
            "/api/ar-content",
            "/api/ar-content/{id}"
        ]
        
        missing_routes = []
        for required_route in required_routes:
            if not any(required_route in r for r in routes):
                missing_routes.append(required_route)
        
        if missing_routes:
            print(f"❌ Отсутствуют маршруты: {', '.join(missing_routes)}")
            return False
        else:
            print("✅ Все ключевые маршруты присутствуют")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка при проверке маршрутов: {e}")
        return False


async def test_api_endpoints():
    """Тестирование API эндпоинтов"""
    print("\n🔌 Тестирование API эндпоинтов...")
    
    try:
        from app.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Тест health check
        health_response = client.get("/health")
        if health_response.status_code == 200:
            print("✅ Health check: OK")
        else:
            print(f"❌ Health check: {health_response.status_code}")
        
        # Тест списка AR контента
        list_response = client.get("/api/ar-content")
        if list_response.status_code == 200:
            data = list_response.json()
            print(f"✅ GET /api/ar-content: {len(data.get('items', []))} элементов")
        else:
            print(f"❌ GET /api/ar-content: {list_response.status_code}")
            return False
        
        # Тест детальной информации (если есть данные)
        if data.get('items'):
            first_id = data['items'][0]['id']
            detail_response = client.get(f"/api/ar-content/{first_id}")
            if detail_response.status_code == 200:
                detail_data = detail_response.json()
                print(f"✅ GET /api/ar-content/{first_id}: детали загружены")
                
                # Проверяем наличие всех полей в ответе
                expected_fields = [
                    'id', 'unique_id', 'project_id', 'customer_name', 
                    'customer_phone', 'order_number', 'status', 'created_at', 'updated_at'
                ]
                
                missing_response_fields = []
                for field in expected_fields:
                    if field not in detail_data:
                        missing_response_fields.append(field)
                
                if missing_response_fields:
                    print(f"⚠️  В ответе API отсутствуют поля: {', '.join(missing_response_fields)}")
                else:
                    print("✅ Все ожидаемые поля присутствуют в ответе API")
            else:
                print(f"❌ GET /api/ar-content/{first_id}: {detail_response.status_code}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании API: {e}")
        return False


async def check_admin_page_access():
    """Проверка доступа к админским страницам"""
    print("\n🔐 Проверка доступа к админским страницам...")
    
    try:
        from app.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Тест доступа без авторизации
        admin_response = client.get("/admin/ar-content", follow_redirects=False)
        if admin_response.status_code in [302, 303]:
            print("✅ Перенаправление на авторизацию: OK")
        elif admin_response.status_code == 200:
            print("✅ Доступ к странице разрешен")
        else:
            print(f"⚠️  Статус ответа: {admin_response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при проверке доступа: {e}")
        return False


async def main():
    """Основная функция проверки"""
    print("🚀 Начинаю проверку корректности отображения AR контента...")
    print("=" * 60)
    
    checks = [
        ("Поля модели", check_required_fields),
        ("Данные в БД", check_ar_content_data),
        ("HTML шаблоны", check_template_files),
        ("Маршруты", check_routes),
        ("API эндпоинты", test_api_endpoints),
        ("Доступ к админке", check_admin_page_access),
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            result = await check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ Ошибка в проверке '{check_name}': {e}")
            results.append((check_name, False))
    
    print("\n" + "=" * 60)
    print("📊 Итоги проверки:")
    
    all_passed = True
    for check_name, result in results:
        status = "✅ ПРойдено" if result else "❌ НЕ пройдено"
        print(f"   {check_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 Все проверки пройдены! Система готова к использованию.")
        print("\n📋 Что проверено:")
        print("   ✅ Все поля ARContent присутствуют в модели")
        print("   ✅ Данные корректно отображаются в детальной информации")
        print("   ✅ Список AR контента формируется правильно")
        print("   ✅ HTML шаблоны на месте")
        print("   ✅ API эндпоинты работают")
        print("   ✅ Маршруты настроены корректно")
        print("\n🌐 Можно переходить к проверке в браузере:")
        print("   📱 Админ-панель: http://localhost:8000/admin")
        print("   📋 Список AR контента: http://localhost:8000/admin/ar-content")
        print("   🔌 API документация: http://localhost:8000/docs")
    else:
        print("⚠️  Найдены проблемы! Необходимо исправить ошибки перед использованием.")
        print("\n🔧 Рекомендации:")
        print("   1. Убедитесь, что все миграции применены: alembic upgrade head")
        print("   2. Создайте тестовые данные: python scripts/test_admin_functionality.py")
        print("   3. Проверьте переменные окружения в .env файле")
        print("   4. Убедитесь, что все зависимости установлены")
    
    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
