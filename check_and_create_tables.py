from sqlalchemy import create_engine, text
from app.core.config import settings
from app.core.database import Base

# Импортируем все модели, чтобы они были зарегистрированы в Base.metadata
from app.models.user import User
from app.models.company import Company
from app.models.project import Project
from app.models.ar_content import ARContent
from app.models.video import Video
from app.models.storage import StorageConnection, StorageFolder
from app.models.folder import Folder
from app.models.client import Client
from app.models.video_schedule import VideoSchedule
from app.models.video_rotation_schedule import VideoRotationSchedule
from app.models.ar_view_session import ARViewSession
from app.models.notification import Notification
from app.models.email_queue import EmailQueue
from app.models.audit_log import AuditLog

import traceback

def check_and_create_tables():
    try:
        # Создаем синхронный движок
        database_url = settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
        print(f"Connecting to database: {database_url}")
        
        engine = create_engine(database_url)
        
        # Проверяем подключение
        with engine.connect() as conn:
            print("Database connection successful")
            
            # Проверяем существование таблицы users
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'users'
                )
            """))
            table_exists = result.scalar()
            print(f'Users table exists: {table_exists}')
            
            if not table_exists:
                print('Users table does not exist, creating all tables...')
                # Создаем все таблицы
                Base.metadata.create_all(engine)
                print('Tables created successfully')
                
                # Проверяем, что таблицы теперь существуют
                result = conn.execute(text("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """))
                tables = [row[0] for row in result.fetchall()]
                print(f'All existing tables: {tables}')
            else:
                print('Users table already exists')
                
                # Проверяем наличие пользователей
                result = conn.execute(text('SELECT id, email, full_name, role FROM users'))
                users = result.fetchall()
                print(f'Found {len(users)} users:')
                for user in users:
                    print(f'  ID: {user[0]}, Email: {user[1]}, Name: {user[2]}, Role: {user[3]}')
                
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    check_and_create_tables()