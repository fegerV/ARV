import asyncio
from app.core.database import engine
from sqlalchemy import text

async def check_admin():
    try:
        async with engine.connect() as conn:
            # Проверим наличие пользователя с ролью admin
            result = await conn.execute(text("SELECT id, email, full_name, role FROM users WHERE role = 'admin'"))
            admin_users = result.fetchall()
            
            if admin_users:
                print("Найдены пользователи с ролью администратора:")
                for user in admin_users:
                    print(f"  ID: {user[0]}, Email: {user[1]}, Имя: {user[2]}, Роль: {user[3]}")
            else:
                print("Пользователи с ролью администратора не найдены.")
                
            # Также проверим наличие любого пользователя с email admin@vertexar.com
            result = await conn.execute(text("SELECT id, email, full_name, role FROM users WHERE email = 'admin@vertexar.com'"))
            specific_admin = result.fetchall()
            
            if specific_admin:
                print("\nНайден пользователь с email admin@vertexar.com:")
                for user in specific_admin:
                    print(f"  ID: {user[0]}, Email: {user[1]}, Имя: {user[2]}, Роль: {user[3]}")
            else:
                print("\nПользователь с email admin@vertexar.com не найден.")
                
    except Exception as e:
        print(f"Ошибка при проверке базы данных: {e}")

if __name__ == "__main__":
    asyncio.run(check_admin())