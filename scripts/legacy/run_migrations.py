"""
Скрипт для выполнения миграций с правильной базой данных
"""
import asyncio
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory
from alembic.runtime.environment import EnvironmentContext
from alembic.runtime.migration import MigrationContext

# Устанавливаем переменные окружения для использования SQLite
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_vertex_ar.db"

def run_migrations():
    """Выполнение миграций для SQLite базы данных"""
    # Создаем конфигурацию Alembic
    alembic_cfg = Config("alembic.ini")
    
    # Устанавливаем URL базы данных
    alembic_cfg.set_main_option("sqlalchemy.url", "sqlite+aiosqlite:///./test_vertex_ar.db")
    
    print("Running migrations for SQLite database...")
    
    # Выполняем миграции до последней версии
    command.upgrade(alembic_cfg, "head")
    
    print("Migrations applied successfully!")
    
    # Проверяем текущую версию
    command.current(alembic_cfg)

if __name__ == "__main__":
    run_migrations()
