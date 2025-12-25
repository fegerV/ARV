#!/usr/bin/env python3
"""
Скрипт для запуска тестового сервера админки с SQLite
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

# Устанавливаем переменные окружения для SQLite
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_vertex_ar.db"
os.environ["ADMIN_EMAIL"] = "admin@vertexar.com"
os.environ["ADMIN_DEFAULT_PASSWORD"] = "admin123"
os.environ["DEBUG"] = "true"
os.environ["ENVIRONMENT"] = "development"

import uvicorn
from app.main import app

def main():
    """Запуск тестового сервера"""
    print("🚀 Запуск тестового сервера админки Vertex AR")
    print("=" * 50)
    print("📋 Данные для входа:")
    print("   Email: admin@vertexar.com")
    print("   Пароль: admin123")
    print("   URL: http://localhost:8000/admin")
    print("   API Docs: http://localhost:8000/docs")
    print("=" * 50)
    print("⚠️  Нажмите Ctrl+C для остановки сервера")
    print("=" * 50)
    
    # Запуск сервера
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()