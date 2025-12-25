#!/usr/bin/env python3
"""
Скрипт для тестирования функциональности админки Vertex AR
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.company import Company
from app.models.project import Project
from app.models.ar_content import ARContent
from app.models.video import Video
from app.models.user import User
from app.core.security import get_password_hash
from app.enums import CompanyStatus, ProjectStatus, ArContentStatus, VideoStatus
from datetime import datetime, timedelta
import uuid

# Настройка SQLite для тестов
SQLITE_DATABASE_URL = "sqlite+aiosqlite:///./test_vertex_ar.db"

async def init_test_db():
    """Инициализация тестовой базы данных SQLite"""
    engine = create_async_engine(
        SQLITE_DATABASE_URL,
        echo=True,
        connect_args={"check_same_thread": False}
    )
    
    # Создаем все таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Создаем фабрику сессий
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    return async_session

async def create_test_data(async_session):
    """Создание тестовых данных"""
    async with async_session() as session:
        try:
            # Создаем администратора
            admin_user = User(
                email="admin@vertexar.com",
                hashed_password=get_password_hash("admin123"),
                full_name="Vertex AR Admin",
                role="admin",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(admin_user)
            await session.flush()
            
            # Создаем компанию Vertex AR
            company = Company(
                name="Vertex AR",
                slug="vertex-ar",
                contact_email="admin@vertexar.com",
                status=CompanyStatus.ACTIVE,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(company)
            await session.flush()
            
            # Создаем проект "Портреты"
            project = Project(
                name="Портреты",
                company_id=company.id,
                status=ProjectStatus.ACTIVE,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(project)
            await session.flush()
            
            # Создаем AR-контент
            ar_content = ARContent(
                name="Тестовый AR-контент",
                project_id=project.id,
                company_id=company.id,
                unique_id=str(uuid.uuid4()),
                order_number="ORDER-001",
                customer_name="Иван Петров",
                customer_phone="+7 (999) 123-45-67",
                customer_email="ivan.petrov@example.com",
                duration_years=3,
                views_count=0,
                status=ArContentStatus.PENDING,
                photo_path="/storage/photos/test_photo.jpg",
                photo_url="http://localhost:8000/storage/photos/test_photo.jpg",
                thumbnail_url="http://localhost:8000/storage/photos/test_photo_thumb.jpg",
                qr_code_path="/storage/qr/test_qr.png",
                qr_code_url="http://localhost:8000/storage/qr/test_qr.png",
                marker_path="/storage/markers/test_marker.mind",
                marker_url="http://localhost:8000/storage/markers/test_marker.mind",
                marker_status="pending",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(ar_content)
            await session.flush()
            
            # Создаем видео для AR-контента
            video1 = Video(
                ar_content_id=ar_content.id,
                filename="video1.mp4",
                video_path="/storage/videos/video1.mp4",
                video_url="http://localhost:8000/storage/videos/video1.mp4",
                thumbnail_path="/storage/videos/video1_thumb.jpg",
                thumbnail_url="http://localhost:8000/storage/videos/video1_thumb.jpg",
                preview_url="http://localhost:8000/storage/videos/video1_preview.jpg",
                duration=30,
                width=1920,
                height=1080,
                size_bytes=5000000,
                mime_type="video/mp4",
                status=VideoStatus.READY,
                is_active=True,
                rotation_type="none",
                rotation_order=1,
                subscription_end=datetime.utcnow() + timedelta(days=3*365),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            video2 = Video(
                ar_content_id=ar_content.id,
                filename="video2.mp4",
                video_path="/storage/videos/video2.mp4",
                video_url="http://localhost:8000/storage/videos/video2.mp4",
                thumbnail_path="/storage/videos/video2_thumb.jpg",
                thumbnail_url="http://localhost:8000/storage/videos/video2_thumb.jpg",
                preview_url="http://localhost:8000/storage/videos/video2_preview.jpg",
                duration=45,
                width=1920,
                height=1080,
                size_bytes=7000000,
                mime_type="video/mp4",
                status=VideoStatus.READY,
                is_active=False,
                rotation_type="none",
                rotation_order=2,
                subscription_end=datetime.utcnow() + timedelta(days=3*365),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            session.add(video1)
            session.add(video2)
            
            # Устанавливаем активное видео
            ar_content.active_video_id = video1.id
            
            await session.commit()
            
            print("✅ Тестовые данные успешно созданы:")
            print(f"   - Администратор: admin@vertexar.com / admin123")
            print(f"   - Компания: Vertex AR (ID: {company.id})")
            print(f"   - Проект: Портреты (ID: {project.id})")
            print(f"   - AR-контент: {ar_content.name} (ID: {ar_content.id})")
            print(f"   - Уникальная ссылка: http://localhost:8000/view/{ar_content.unique_id}")
            print(f"   - Активное видео: {video1.filename}")
            print(f"   - Всего видео: 2")
            
            return {
                'admin_email': 'admin@vertexar.com',
                'admin_password': 'admin123',
                'company_id': company.id,
                'project_id': project.id,
                'ar_content_id': ar_content.id,
                'unique_id': ar_content.unique_id,
                'active_video_id': video1.id
            }
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Ошибка при создании тестовых данных: {e}")
            raise

async def verify_data_structure(async_session):
    """Проверка структуры данных"""
    async with async_session() as session:
        try:
            # Проверяем компании
            from sqlalchemy import select
            companies_result = await session.execute(select(Company))
            companies = companies_result.scalars().all()
            print(f"\n📊 Компании в базе: {len(companies)}")
            for company in companies:
                print(f"   - {company.name} (slug: {company.slug}, статус: {company.status})")
            
            # Проверяем проекты
            projects_result = await session.execute(select(Project))
            projects = projects_result.scalars().all()
            print(f"\n📊 Проекты в базе: {len(projects)}")
            for project in projects:
                print(f"   - {project.name} (статус: {project.status})")
            
            # Проверяем AR-контент
            ar_contents_result = await session.execute(select(ARContent))
            ar_contents = ar_contents_result.scalars().all()
            print(f"\n📊 AR-контент в базе: {len(ar_contents)}")
            for content in ar_contents:
                print(f"   - {content.name or 'Без имени'} (заказ: {content.order_number}, статус: {content.status})")
                print(f"     Уникальная ссылка: /view/{content.unique_id}")
                print(f"     Клиент: {content.customer_name}")
            
            # Проверяем видео
            videos_result = await session.execute(select(Video))
            videos = videos_result.scalars().all()
            print(f"\n📊 Видео в базе: {len(videos)}")
            for video in videos:
                status_icon = "🟢" if video.is_active else "⚪"
                print(f"   {status_icon} {video.filename} (статус: {video.status}, активное: {video.is_active})")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при проверке данных: {e}")
            return False

async def main():
    """Главная функция"""
    print("🚀 Запуск тестирования админки Vertex AR")
    print("=" * 50)
    
    try:
        # Инициализация базы данных
        print("📦 Инициализация SQLite базы данных...")
        async_session = await init_test_db()
        
        # Создание тестовых данных
        print("📝 Создание тестовых данных...")
        test_data = await create_test_data(async_session)
        
        # Проверка структуры
        print("🔍 Проверка структуры данных...")
        await verify_data_structure(async_session)
        
        print("\n" + "=" * 50)
        print("✅ Тестирование успешно завершено!")
        print("\n📋 Данные для входа в админку:")
        print(f"   Email: {test_data['admin_email']}")
        print(f"   Пароль: {test_data['admin_password']}")
        print(f"   URL: http://localhost:8000/admin")
        print(f"\n🔗 Демо-контент:")
        print(f"   Проект: Портреты")
        print(f"   AR-контент: http://localhost:8000/view/{test_data['unique_id']}")
        print(f"   База данных: {SQLITE_DATABASE_URL}")
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)