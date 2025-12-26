from sqlalchemy import create_engine, text
from app.core.config import settings

def check_admin_user():
    # Создаем синхронный движок
    database_url = settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
    print(f"Connecting to database: {database_url}")
    
    engine = create_engine(database_url)
    
    # Проверяем наличие пользователей
    with engine.connect() as conn:
        # Проверяем пользователя из настроек
        result = conn.execute(text('SELECT id, email, full_name, role FROM users WHERE email = :email'), 
                             {'email': settings.ADMIN_EMAIL})
        user_from_settings = result.fetchone()
        
        print(f"User from settings ({settings.ADMIN_EMAIL}):")
        if user_from_settings:
            print(f"  Found: ID={user_from_settings[0]}, Email={user_from_settings[1]}, Name={user_from_settings[2]}, Role={user_from_settings[3]}")
        else:
            print("  Not found")
        
        # Проверяем пользователя из миграции
        result = conn.execute(text('SELECT id, email, full_name, role FROM users WHERE email = :email'), 
                             {'email': 'admin@vertex.local'})
        user_from_migration = result.fetchone()
        
        print(f"User from migration (admin@vertex.local):")
        if user_from_migration:
            print(f"  Found: ID={user_from_migration[0]}, Email={user_from_migration[1]}, Name={user_from_migration[2]}, Role={user_from_migration[3]}")
        else:
            print("  Not found")
        
        # Показываем всех пользователей
        result = conn.execute(text('SELECT id, email, full_name, role FROM users'))
        all_users = result.fetchall()
        print(f"All users in database ({len(all_users)}):")
        for user in all_users:
            print(f"  ID: {user[0]}, Email: {user[1]}, Name: {user[2]}, Role: {user[3]}")

if __name__ == "__main__":
    check_admin_user()