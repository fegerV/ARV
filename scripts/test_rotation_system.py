"""Простой тест для проверки системы ротации видео."""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.models.ar_content import ARContent
from app.models.video import Video
from app.models.video_rotation_schedule import VideoRotationSchedule
from app.services.video_scheduler import get_active_video, get_rotation_rule


async def test_rotation_system():
    """Тестирует систему ротации видео."""
    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
    )
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as db:
        print("=" * 60)
        print("Тест системы ротации видео")
        print("=" * 60)
        
        # 1. Проверка наличия AR контента
        print("\n1. Проверка наличия AR контента...")
        stmt = select(ARContent).limit(1)
        result = await db.execute(stmt)
        ar_content = result.scalar_one_or_none()
        
        if not ar_content:
            print("   [X] AR контент не найден. Создайте хотя бы один AR контент.")
            return
        
        print(f"   [OK] Найден AR контент: ID={ar_content.id}, Order={ar_content.order_number}")
        
        # 2. Проверка наличия видео
        print("\n2. Проверка наличия видео...")
        stmt = select(Video).where(Video.ar_content_id == ar_content.id)
        result = await db.execute(stmt)
        videos = list(result.scalars().all())
        
        if not videos:
            print("   [X] Видео не найдены. Добавьте хотя бы одно видео.")
            return
        
        print(f"   [OK] Найдено видео: {len(videos)} шт.")
        for video in videos:
            print(f"      - ID={video.id}, Filename={video.filename}, Active={video.is_active}")
        
        # 3. Проверка расписания ротации
        print("\n3. Проверка расписания ротации...")
        rotation_rule = await get_rotation_rule(ar_content.id, db)
        
        if rotation_rule:
            print(f"   [OK] Расписание найдено: ID={rotation_rule.id}")
            print(f"      - Тип: {rotation_rule.rotation_type}")
            print(f"      - Активно: {rotation_rule.is_active}")
            print(f"      - Видео по умолчанию: {rotation_rule.default_video_id}")
            if rotation_rule.video_sequence:
                print(f"      - Последовательность: {rotation_rule.video_sequence}")
            if rotation_rule.date_rules:
                print(f"      - Правила по датам: {len(rotation_rule.date_rules)} шт.")
        else:
            print("   [WARN] Расписание ротации не настроено (используется фиксированное видео)")
        
        # 4. Проверка получения активного видео
        print("\n4. Проверка получения активного видео...")
        active_data = await get_active_video(ar_content.id, db)
        
        if active_data and active_data.get("video"):
            active_video = active_data["video"]
            print(f"   [OK] Активное видео: ID={active_video.id}, Filename={active_video.filename}")
            print(f"      - Источник: {active_data.get('source', 'unknown')}")
            if active_data.get("expires_in"):
                print(f"      - Истекает через: {active_data['expires_in']} дней")
        else:
            print("   [X] Активное видео не найдено")
        
        # 5. Проверка структуры базы данных
        print("\n5. Проверка структуры базы данных...")
        try:
            # Проверка наличия колонки rotation_state в ARContent
            if hasattr(ar_content, 'rotation_state'):
                print(f"   [OK] ARContent.rotation_state: {ar_content.rotation_state}")
            else:
                print("   [X] ARContent.rotation_state не найден")
            
            # Проверка наличия полей в Video
            if videos:
                video = videos[0]
                if hasattr(video, 'rotation_weight'):
                    print(f"   [OK] Video.rotation_weight: {video.rotation_weight}")
                else:
                    print("   [X] Video.rotation_weight не найден")
                
                if hasattr(video, 'is_default'):
                    print(f"   [OK] Video.is_default: {video.is_default}")
                else:
                    print("   [X] Video.is_default не найден")
        except Exception as e:
            print(f"   [X] Ошибка проверки структуры: {e}")
        
        print("\n" + "=" * 60)
        print("Тест завершен")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_rotation_system())
