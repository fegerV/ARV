#!/usr/bin/env python3
"""
Скрипт для запуска тестового сервера с SQLite базой данных
"""

import os
import sys
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

# Устанавливаем переменные окружения для SQLite
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_vertex_ar.db"
os.environ["DEBUG"] = "true"
os.environ["ADMIN_EMAIL"] = "admin@vertexar.com"
os.environ["ADMIN_DEFAULT_PASSWORD"] = "admin123"
os.environ["SECRET_KEY"] = "test-secret-key-for-development"
os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://localhost:8000"
os.environ["MEDIA_ROOT"] = "./storage/content"
os.environ["STORAGE_BASE_PATH"] = "./storage/content"
os.environ["LOCAL_STORAGE_PATH"] = "./storage/content"
os.environ["TEMPLATES_DIR"] = "./templates"
os.environ["STATIC_DIR"] = "./static"

if __name__ == "__main__":
    import uvicorn
    from app.main import app
    
    print("🚀 Запуск тестового сервера Vertex AR...")
    print("📊 База данных: SQLite (test_vertex_ar.db)")
    print("🔐 Админ доступ: http://localhost:8000/admin")
    print("📋 Логин: admin@vertexar.com / admin123")
    print("📱 AR контент: http://localhost:8000/ar-content/1")
    print("🔗 Публичный просмотр: http://localhost:8000/view/35278433-2cd3-49e5-8d76-908830e5e0ff")
    print("=" * 60)
    
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )