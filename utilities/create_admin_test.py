#!/usr/bin/env python3
"""
Создание администратора для Vertex AR Platform
"""
import asyncio
import sys
import os
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select

async def create_admin():
    """Создание администратора"""
    new_password = os.environ.get("ADMIN_DEFAULT_PASSWORD", "")
    if not new_password:
        print("Error: ADMIN_DEFAULT_PASSWORD environment variable is not set")
        return False
    
    print("🔧 Создание администратора Vertex AR Platform...")
    
    async with AsyncSessionLocal() as session:
        try:
            # Проверяем, существует ли администратор
            result = await session.execute(
                select(User).where(User.email == "admin@vertexar.com")
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print("✅ Администратор уже существует")
                print(f"   Email: {existing_user.email}")
                print(f"   Имя: {existing_user.full_name}")
                print(f"   Роль: {existing_user.role}")
                return True
            
            # Создаем нового администратора
            admin_user = User(
                email="admin@vertexar.com",
                full_name="Vertex AR Admin",
                hashed_password=get_password_hash(new_password),
                role="admin",
                is_active=True
            )
            
            session.add(admin_user)
            await session.commit()
            await session.refresh(admin_user)
            
            print("✅ Администратор успешно создан!")
            print(f"   Email: admin@vertexar.com")
            print(f"   ID: {admin_user.id}")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при создании администратора: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Главная функция"""
    print("=" * 60)
    print("🔧 СОЗДАНИЕ АДМИНИСТРАТОРА")
    print("=" * 60)
    
    success = await create_admin()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ АДМИНИСТРАТОР УСПЕШНО СОЗДАН")
    else:
        print("❌ ОШИБКА СОЗДАНИЯ АДМИНИСТРАТОРА")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())