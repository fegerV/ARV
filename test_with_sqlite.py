import os
import sys
import asyncio
import uvicorn
from fastapi import FastAPI

# Изменяем настройки для использования SQLite вместо PostgreSQL
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./test.db'

# Импортируем приложение после изменения переменной окружения
from app.main import app

if __name__ == "__main__":
    print("Запуск сервера с SQLite...")
    try:
        # Запускаем сервер
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    except KeyboardInterrupt:
        print("Сервер остановлен пользователем")
    except Exception as e:
        print(f"Ошибка при запуске сервера: {e}")
        import traceback
        traceback.print_exc()