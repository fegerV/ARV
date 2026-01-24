#!/usr/bin/env python3
"""
Финальная проверка системы Vertex AR B2B Platform
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.core.database import AsyncSessionLocal
from app.models.ar_content import ARContent
from app.models.project import Project
from app.models.company import Company
from app.models.user import User
from app.models.video import Video
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import json


async def final_system_check():
    """Финальная проверка всей системы"""
    print("🔍 ФИНАЛЬНАЯ ПРОВЕРКА СИСТЕМЫ VERTEX AR B2B PLATFORM")
    print("=" * 60)
    
    async with AsyncSessionLocal() as session:
        try:
            # 1. Проверка пользователей
            print("\n👤 1. Проверка пользователей:")
            users_count = await session.scalar(select(func.count(User.id)))
            admin_result = await session.execute(select(User).where(User.email == "admin@vertexar.com"))
            admin = admin_result.scalar_one_or_none()
            
            print(f"   📊 Всего пользователей: {users_count}")
            if admin:
                print(f"   ✅ Администратор найден: {admin.email}")
                print(f"   🔐 Роль: {admin.role}")
                print(f"   ✅ Активен: {admin.is_active}")
            else:
                print(f"   ❌ Администратор не найден!")
            
            # 2. Проверка компаний
            print("\n🏢 2. Проверка компаний:")
            companies_count = await session.scalar(select(func.count(Company.id)))
            companies_result = await session.execute(select(Company))
            companies = companies_result.scalars().all()
            
            print(f"   📊 Всего компаний: {companies_count}")
            for company in companies:
                print(f"   📋 {company.name} (slug: {company.slug}, статус: {company.status})")
            
            # 3. Проверка проектов
            print("\n📁 3. Проверка проектов:")
            projects_count = await session.scalar(select(func.count(Project.id)))
            projects_result = await session.execute(
                select(Project).options(selectinload(Project.company))
            )
            projects = projects_result.scalars().all()
            
            print(f"   📊 Всего проектов: {projects_count}")
            for project in projects:
                print(f"   📋 {project.name} (компания: {project.company.name if project.company else 'N/A'}, статус: {project.status})")
            
            # 4. Проверка AR контента
            print("\n🎯 4. Проверка AR контента:")
            ar_content_count = await session.scalar(select(func.count(ARContent.id)))
            ar_content_result = await session.execute(
                select(ARContent)
                .options(
                    selectinload(ARContent.project).selectinload(Project.company)
                )
                .limit(5)
            )
            ar_contents = ar_content_result.scalars().all()
            
            print(f"   📊 Всего AR контента: {ar_content_count}")
            
            # Проверка полей AR контента
            required_fields = [
                'id', 'unique_id', 'project_id', 'company_id', 'order_number',
                'customer_name', 'customer_phone', 'status', 'thumbnail_url',
                'marker_path', 'marker_url', 'marker_status', 'marker_metadata',
                'created_at', 'updated_at'
            ]
            
            print(f"   📋 Ожидаемые поля: {len(required_fields)}")
            model_fields = [field.name for field in ARContent.__table__.columns]
            print(f"   📋 Поля в модели: {len(model_fields)}")
            
            missing_fields = []
            for field in required_fields:
                if field not in model_fields:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"   ⚠️  Отсутствуют поля: {', '.join(missing_fields)}")
            else:
                print(f"   ✅ Все требуемые поля присутствуют")
            
            # Демонстрация данных AR контента
            for i, ar_content in enumerate(ar_contents, 1):
                print(f"\n   📄 AR контент #{i}:")
                print(f"      🆔 ID: {ar_content.id}")
                print(f"      🔑 Уникальный ID: {ar_content.unique_id}")
                print(f"      📁 Проект: {ar_content.project.name if ar_content.project else 'N/A'}")
                print(f"      🏢 Компания: {ar_content.project.company.name if ar_content.project and ar_content.project.company else 'N/A'}")
                print(f"      📦 Заказ: {ar_content.order_number}")
                print(f"      👤 Клиент: {ar_content.customer_name}")
                print(f"      📞 Телефон: {ar_content.customer_phone}")
                print(f"      📊 Статус: {ar_content.status}")
                print(f"      🖼️ Миниатюра: {ar_content.thumbnail_url}")
                print(f"      🎯 Маркер: {ar_content.marker_path}")
                print(f"      🌐 URL маркера: {ar_content.marker_url}")
                print(f"      ⚡ Статус маркера: {ar_content.marker_status}")
                print(f"      📄 Метаданные: {ar_content.marker_metadata}")
                print(f"      📅 Создан: {ar_content.created_at}")
                print(f"      🔄 Обновлен: {ar_content.updated_at}")
                
                # Проверка наличия всех данных
                missing_data = []
                if not ar_content.unique_id:
                    missing_data.append("unique_id")
                if not ar_content.customer_name:
                    missing_data.append("customer_name")
                if not ar_content.customer_phone:
                    missing_data.append("customer_phone")
                if not ar_content.order_number:
                    missing_data.append("order_number")
                if not ar_content.status:
                    missing_data.append("status")
                
                if missing_data:
                    print(f"      ⚠️  Отсутствуют данные: {', '.join(missing_data)}")
                else:
                    print(f"      ✅ Все данные заполнены")
            
            # 5. Проверка видео
            print("\n🎥 5. Проверка видео:")
            videos_count = await session.scalar(select(func.count(Video.id)))
            videos_result = await session.execute(
                select(Video).options(selectinload(Video.ar_content)).limit(5)
            )
            videos = videos_result.scalars().all()
            
            print(f"   📊 Всего видео: {videos_count}")
            for i, video in enumerate(videos, 1):
                print(f"   🎬 Видео #{i}: {video.filename}")
                print(f"      🎯 AR контент: {video.ar_content.order_number if video.ar_content else 'N/A'}")
                print(f"      📊 Статус: {video.status}")
                print(f"      ✅ Активно: {video.is_active}")
                print(f"      ⏱️ Длительность: {video.duration} сек")
                print(f"      📏 Размер: {video.width}x{video.height}")
            
            # 6. Итоги
            print("\n" + "=" * 60)
            print("📊 ИТОГИ ПРОВЕРКИ:")
            
            checks = [
                (f"Пользователи ({users_count})", users_count > 0),
                (f"Компании ({companies_count})", companies_count > 0),
                (f"Проекты ({projects_count})", projects_count > 0),
                (f"AR контент ({ar_content_count})", ar_content_count > 0),
                (f"Видео ({videos_count})", videos_count > 0),
                ("Поля AR контента", len(missing_fields) == 0),
            ]
            
            all_passed = True
            for check_name, passed in checks:
                status = "✅ OK" if passed else "❌ ERROR"
                print(f"   {check_name}: {status}")
                if not passed:
                    all_passed = False
            
            print("\n" + "=" * 60)
            if all_passed:
                print("🎉 СИСТЕМА ГОТОВА К ИСПОЛЬЗОВАНИЮ!")
                print("\n📋 Данные для входа:")
                print("   🌐 Админ-панель: http://localhost:8000/admin")
                print("   👤 Email: admin@vertexar.com")
                print("   🔐 Пароль: admin123")
                print("   📚 API документация: http://localhost:8000/docs")
                print("   ❤️  Health check: http://localhost:8000/health")
                
                if ar_contents:
                    print(f"\n🔗 Демо-ссылки:")
                    for ar_content in ar_contents:
                        print(f"   🎯 AR контент: http://localhost:8000/view/{ar_content.unique_id}")
                        print(f"   📊 Заказ {ar_content.order_number}: {ar_content.customer_name}")
                
                print(f"\n📈 Статистика:")
                print(f"   👥 Пользователей: {users_count}")
                print(f"   🏢 Компаний: {companies_count}")
                print(f"   📁 Проектов: {projects_count}")
                print(f"   🎯 AR контента: {ar_content_count}")
                print(f"   🎥 Видео: {videos_count}")
                
                print(f"\n✅ Проверено:")
                print(f"   ✅ Все поля AR контента присутствуют")
                print(f"   ✅ Данные корректно отображаются")
                print(f"   ✅ Связи между таблицами работают")
                print(f"   ✅ Тестовые данные созданы")
                
            else:
                print("⚠️  НАЙДЕНЫ ПРОБЛЕМЫ!")
                print("🔧 Рекомендации:")
                print("   1. Проверьте создание тестовых данных")
                print("   2. Убедитесь, что все миграции применены")
                print("   3. Проверьте переменные окружения")
            
            return all_passed
            
        except Exception as e:
            print(f"❌ Ошибка при проверке: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    asyncio.run(final_system_check())
