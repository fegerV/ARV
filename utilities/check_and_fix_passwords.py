from sqlalchemy import create_engine, text
from app.core.config import settings
from app.core.security import verify_password, get_password_hash
import os

def check_and_fix_passwords():
    admin_password = os.environ.get("ADMIN_DEFAULT_PASSWORD", "")
    if not admin_password:
        print("Error: ADMIN_DEFAULT_PASSWORD environment variable is not set")
        return
    
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
            
            # Проверяем, можно ли расшифровать пароль
            test_passwords = [admin_password]
            
            valid_password = None
            for pwd in test_passwords:
                if not pwd:
                    continue
                if verify_password(pwd, user[2]):
                    valid_password = pwd
                    break
            
            if valid_password:
                print(f"    Password verification successful with provided password")
            else:
                print(f"    Password verification failed")
                
                # Обновляем пароль для пользователя, если он использует стандартный email
                if user[1] == settings.ADMIN_EMAIL:
                    new_hash = get_password_hash(admin_password)
                    conn.execute(
                        text('UPDATE users SET hashed_password = :new_hash WHERE id = :user_id'),
                        {'new_hash': new_hash, 'user_id': user[0]}
                    )
                    conn.commit()
                    print(f"    Updated password for {user[1]} to use settings.ADMIN_DEFAULT_PASSWORD")

if __name__ == "__main__":
    check_and_fix_passwords()