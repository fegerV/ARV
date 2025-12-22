from sqlalchemy import create_engine, text
from app.core.config import settings
from app.core.security import verify_password, get_password_hash

def test_auth():
    # Создаем синхронный движок
    database_url = settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
    print(f"Connecting to database: {database_url}")
    
    engine = create_engine(database_url)
    
    # Получаем пользователя из базы данных
    with engine.connect() as conn:
        result = conn.execute(text('SELECT id, email, hashed_password, full_name, role FROM users WHERE email = :email'), 
                             {'email': 'admin@vertex.local'})
        user = result.fetchone()
        
        if user:
            print(f"User found: ID={user[0]}, Email={user[1]}, Name={user[3]}, Role={user[4]}")
            
            # Проверяем пароль (в миграции seed_initial_data используется 'admin123')
            test_password = 'admin123'
            stored_hash = user[2]
            
            if verify_password(test_password, stored_hash):
                print("Password verification successful!")
                print(f"Login credentials: email='admin@vertex.local', password='admin123'")
            else:
                print("Password verification failed!")
                print(f"Stored hash: {stored_hash}")
        else:
            print("Admin user not found!")

if __name__ == "__main__":
    test_auth()