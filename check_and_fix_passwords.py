from sqlalchemy import create_engine, text
from app.core.config import settings
from app.core.security import verify_password, get_password_hash

def check_and_fix_passwords():
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
            test_passwords = ['admin123', 'ChangeMe123!']
            
            valid_password = None
            for pwd in test_passwords:
                if verify_password(pwd, user[2]):
                    valid_password = pwd
                    break
            
            if valid_password:
                print(f"    Password verification successful with: '{valid_password}'")
            else:
                print(f"    Password verification failed for both test passwords")
                print(f"    Stored hash: {user[2][:20]}..." if len(user[2]) > 20 else f"    Stored hash: {user[2]}")
                
                # Обновляем пароль для пользователя, если он использует стандартный email
                if user[1] == settings.ADMIN_EMAIL:
                    new_hash = get_password_hash(settings.ADMIN_DEFAULT_PASSWORD)
                    conn.execute(
                        text('UPDATE users SET hashed_password = :new_hash WHERE id = :user_id'),
                        {'new_hash': new_hash, 'user_id': user[0]}
                    )
                    conn.commit()
                    print(f"    Updated password for {user[1]} to use settings.ADMIN_DEFAULT_PASSWORD")
                elif user[1] == 'admin@vertex.local':
                    new_hash = get_password_hash('admin123')  # пароль из миграции
                    conn.execute(
                        text('UPDATE users SET hashed_password = :new_hash WHERE id = :user_id'),
                        {'new_hash': new_hash, 'user_id': user[0]}
                    )
                    conn.commit()
                    print(f"    Updated password for {user[1]} to 'admin123'")

if __name__ == "__main__":
    check_and_fix_passwords()