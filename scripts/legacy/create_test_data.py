"""
Скрипт для создания тестовых данных для Vertex AR
"""
import asyncio
import sys
from pathlib import Path
import os

# Устанавливаем переменную окружения для использования SQLite до импорта модулей приложения
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_vertex_ar.db"

# Добавляем текущую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.company import Company
from app.models.project import Project
from app.models.ar_content import ARContent
from app.models.video import Video
from app.core.security import get_password_hash
from app.enums import CompanyStatus, ProjectStatus, ArContentStatus, VideoStatus
import uuid
from datetime import datetime, timedelta


async def create_test_data():
    """Создание тестовых данных"""
    # Создаем асинхронный движок для SQLite
    engine = create_async_engine("sqlite+aiosqlite:///./test_vertex_ar.db")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("Creating test data...")
        
        # 1. Проверяем и создаем админа
        result = await session.execute(select(User).where(User.email == "admin@vertexar.com"))
        admin = result.scalar_one_or_none()
        
        if not admin:
            admin = User(
                email="admin@vertexar.com",
                hashed_password=get_password_hash("admin123"),
                full_name="Vertex AR Admin",
                role="admin",
                is_active=True,
            )
            session.add(admin)
            await session.flush()
            print("Admin created: admin@vertexar.com / admin123")
        else:
            print("Admin already exists")
        
        # 2. Проверяем и создаем компанию
        result = await session.execute(select(Company).where(Company.name == "Vertex AR"))
        company = result.scalar_one_or_none()
        
        if not company:
            company = Company(
                name="Vertex AR",
                slug="vertex-ar",
                contact_email="admin@vertexar.com",
                status=CompanyStatus.ACTIVE,
            )
            session.add(company)
            await session.flush()
            print("Company created: Vertex AR")
        else:
            print("Company already exists")
        
        # 3. Проверяем и создаем проект
        result = await session.execute(
            select(Project).where(
                (Project.company_id == company.id) & 
                (Project.name == "Portraits")
            )
        )
        project = result.scalar_one_or_none()
        
        if not project:
            project = Project(
                name="Portraits",
                company_id=company.id,
                status=ProjectStatus.ACTIVE,
            )
            session.add(project)
            await session.flush()
            print("Project created: Portraits")
        else:
            print("Project already exists")
        
        # 4. Проверяем и создаем AR контент
        result = await session.execute(
            select(ARContent).where(
                (ARContent.project_id == project.id) & 
                (ARContent.order_number == "ORDER-001")
            )
        )
        ar_content = result.scalar_one_or_none()
        
        unique_id = uuid.UUID("68ae0d72-af16-437b-9f44-f6b59ffd6222")
        
        if not ar_content:
            ar_content = ARContent(
                project_id=project.id,
                company_id=company.id,
                unique_id=str(unique_id),
                order_number="ORDER-001",
                customer_name="Ivan Petrov",
                customer_phone="+7 (999) 123-45-67",
                customer_email="ivan.petrov@example.com",
                duration_years=3,
                views_count=0,
                status=ArContentStatus.ACTIVE,
                photo_path="tmp/storage/test_photo.jpg",
                photo_url="http://localhost:8000/storage/test_photo.jpg",
                video_path="tmp/storage/test_video.mp4",
                video_url="http://localhost:8000/storage/test_video.mp4",
                qr_code_path="tmp/storage/qr_code.png",
                qr_code_url="http://localhost:8000/storage/qr_code.png",
                marker_path="tmp/storage/marker.mind",
                marker_url="http://localhost:8000/storage/marker.mind",
                marker_status="ready",
            )
            session.add(ar_content)
            await session.flush()
            print("AR content created: ORDER-001 - Ivan Petrov")
        else:
            print("AR content already exists")
        
        # 5. Создаем видео для AR контента
        result = await session.execute(
            select(Video).where(Video.ar_content_id == ar_content.id)
        )
        existing_videos = result.scalars().all()
        
        if len(existing_videos) == 0:
            # Первое видео (активное)
            video1 = Video(
                ar_content_id=ar_content.id,
                filename="video1.mp4",
                video_path="tmp/storage/video1.mp4",
                video_url="http://localhost:8000/storage/video1.mp4",
                thumbnail_path="tmp/storage/video1_thumb.jpg",
                thumbnail_url="http://localhost:8000/storage/video1_thumb.jpg",
                preview_url="http://localhost:8000/storage/video1.mp4",
                duration=30,
                width=1920,
                height=1080,
                size_bytes=5242880,
                mime_type="video/mp4",
                status=VideoStatus.READY,
                is_active=True,
                rotation_type="none",
                rotation_order=0,
                subscription_end=datetime.utcnow() + timedelta(days=365*3),
            )
            session.add(video1)
            await session.flush()
            
            # Второе видео (неактивное)
            video2 = Video(
                ar_content_id=ar_content.id,
                filename="video2.mp4",
                video_path="tmp/storage/video2.mp4",
                video_url="http://localhost:8000/storage/video2.mp4",
                thumbnail_path="tmp/storage/video2_thumb.jpg",
                thumbnail_url="http://localhost:8000/storage/video2_thumb.jpg",
                preview_url="http://localhost:8000/storage/video2.mp4",
                duration=45,
                width=1920,
                height=1080,
                size_bytes=7864320,
                mime_type="video/mp4",
                status=VideoStatus.READY,
                is_active=False,
                rotation_type="none",
                rotation_order=1,
                subscription_end=datetime.utcnow() + timedelta(days=365*3),
            )
            session.add(video2)
            await session.flush()
            
            # Устанавливаем активное видео
            ar_content.active_video_id = video1.id
            
            print("Created 2 videos (1 active, 1 inactive)")
        else:
            print(f"Videos already exist ({len(existing_videos)} items)")
        
        # Сохраняем все изменения
        await session.commit()
        
        print("\n" + "="*50)
        print("TEST DATA CREATED SUCCESSFULLY!")
        print("="*50)
        print("\nLOGIN DATA:")
        print(f"   Email: admin@vertexar.com")
        print(f"   Password: admin123")
        print("\nTEST DATA:")
        print(f"   Company: Vertex AR (ID: {company.id})")
        print(f"   Project: Portraits (ID: {project.id})")
        print(f"   AR-content: ORDER-001 - Ivan Petrov (ID: {ar_content.id})")
        print(f"   Unique link: http://localhost:8000/view/{unique_id}")
        print(f"   Videos: {len(existing_videos) if existing_videos else 2} videos")
        print("\nSERVER READY FOR TESTING!")
        print(f"   Admin panel: http://localhost:8000/admin")
        print(f"   API docs: http://localhost:8000/docs")
        print("="*50)


if __name__ == "__main__":
    asyncio.run(create_test_data())
