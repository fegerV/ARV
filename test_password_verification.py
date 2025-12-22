from sqlalchemy import create_engine, text
from app.core.config import settings
from app.core.security import verify_password, get_password_hash

def test_password_verification():
    # Создаем синхронный движок
    database_url = settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
    print(f"Connecting to database: {database_url}")
    
    engine = create_engine(database_url)
    
    # Получаем всех пользователей из базы данных
    with engine.connect() as conn:
        result = conn.execute(text('SELECT id, email, hashed_password, full_name, role FROM users'))
        users = result.fetchall()
        
        print(f"Found {len(users)} users:")
        for user in users:
            print(f"  ID: {user[0]}, Email: {user[1]}, Name: {user[2]}, Role: {user[3]}")
            
            # Тестируем различные возможные пароли
            possible_passwords = [
                'admin123',
                'ChangeMe123!',
                settings.ADMIN_DEFAULT_PASSWORD,
                'admin@vertex.local',  # иногда пароли совпадают с email
                'password',
                '123456'
            ]
            
            print(f"    Testing passwords for user {user[1]}:")
            found_correct = False
            for pwd in possible_passwords:
                if verify_password(pwd, user[2]):
                    print(f"      [OK] '{pwd}' works!")
                    found_correct = True
                    break
                else:
                    print(f"      [FAIL] '{pwd}' doesn't work")
            
            if not found_correct:
                print(f"      No known password works for this user")
            
            print()

if __name__ == "__main__":
    test_password_verification()