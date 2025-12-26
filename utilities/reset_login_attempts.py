#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import create_engine, text
from app.core.config import settings

def reset_login_attempts():
    # Создаем синхронный движок
    database_url = settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
    print(f"Connecting to database: {database_url}")
    
    engine = create_engine(database_url)

    # Сбрасываем попытки входа и блокировку для всех пользователей
    with engine.connect() as conn:
        # Начинаем транзакцию
        trans = conn.begin()
        try:
            # Сбрасываем попытки входа и блокировку
            conn.execute(text('UPDATE users SET login_attempts = 0, locked_until = NULL'))
            trans.commit()
            print("Login attempts and locks have been reset for all users")
            
            # Показываем обновленное состояние пользователей
            result = conn.execute(text('SELECT id, email, full_name, role, is_active, login_attempts, locked_until FROM users ORDER BY id'))
            users = result.fetchall()
            print(f'\nUpdated users ({len(users)}):')
            for user in users:
                print(f'  ID: {user[0]}, Email: {user[1]}, Name: {user[2]}, Role: {user[3]}, Active: {user[4]}, Login attempts: {user[5]}, Locked until: {user[6]}')
                
        except Exception as e:
            trans.rollback()
            print(f"Error occurred: {e}")

if __name__ == "__main__":
    reset_login_attempts()