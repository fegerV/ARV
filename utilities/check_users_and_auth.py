#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import create_engine, text
from app.core.config import settings

def check_users_and_auth():
    # Создаем синхронный движок
    database_url = settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
    print(f"Connecting to database: {database_url}")
    
    engine = create_engine(database_url)

    # Проверяем дубликаты email
    with engine.connect() as conn:
        result = conn.execute(text('''
            SELECT email, COUNT(*) as count 
            FROM users 
            GROUP BY email 
            HAVING COUNT(*) > 1
        '''))
        duplicates = result.fetchall()
        
        if duplicates:
            print('Found duplicate emails:')
            for dup in duplicates:
                print(f'  {dup[0]}: {dup[1]} times')
        else:
            print('No duplicate emails found')
            
        # Показываем всех пользователей
        result = conn.execute(text('SELECT id, email, full_name, role, is_active, login_attempts, locked_until FROM users ORDER BY id'))
        users = result.fetchall()
        print(f'\nAll users ({len(users)}):')
        for user in users:
            print(f'  ID: {user[0]}, Email: {user[1]}, Name: {user[2]}, Role: {user[3]}, Active: {user[4]}, Login attempts: {user[5]}, Locked until: {user[6]}')

if __name__ == "__main__":
    check_users_and_auth()