#!/usr/bin/env python3
"""
Скрипт для запуска тестового сервера админки с SQLite
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Устанавливаем переменные окружения для SQLite
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_vertex_ar.db"
os.environ["ADMIN_EMAIL"] = "admin@vertexar.com"
os.environ["ADMIN_DEFAULT_PASSWORD"] = "admin123"
os.environ["DEBUG"] = "true"
os.environ["ENVIRONMENT"] = "development"
storage_root = Path("./storage/content").resolve()
storage_root.mkdir(parents=True, exist_ok=True)
os.environ["MEDIA_ROOT"] = str(storage_root)
os.environ["LOCAL_STORAGE_PATH"] = str(storage_root)
os.environ["STORAGE_BASE_PATH"] = str(storage_root)
os.environ["LOCAL_STORAGE_PUBLIC_URL"] = "http://127.0.0.1:8000/storage"

import uvicorn
from app.main import app

def main():
    """Запуск тестового сервера"""
    print("Starting Vertex AR admin test server")
    print("=" * 50)
    print("Login details:")
    print("   Email: admin@vertexar.com")
    print("   Password: admin123")
    print("   URL: http://localhost:8000/admin")
    print("   API Docs: http://localhost:8000/docs")
    print("=" * 50)
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Запуск сервера
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
