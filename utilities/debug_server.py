import os
import sys
import asyncio
import uvicorn
from app.main import app

if __name__ == "__main__":
    print("Запуск сервера...")
    try:
        # Запускаем сервер в блокирующем режиме на 10 секунд для теста
        config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
        server = uvicorn.Server(config)
        print("Сервер сконфигурирован, запускаем...")
        asyncio.run(server.serve())
    except KeyboardInterrupt:
        print("Сервер остановлен пользователем")
    except Exception as e:
        print(f"Ошибка при запуске сервера: {e}")
        import traceback
        traceback.print_exc()