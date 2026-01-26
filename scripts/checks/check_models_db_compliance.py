"""
Скрипт для проверки соответствия моделей SQLAlchemy структуре базы данных.
Проверяет все модели и выявляет несоответствия колонок.
"""
import sys
import os
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import inspect, create_engine
import asyncio
from app.core.config import settings
from app.models import (
    User, Company, Project, Folder, Client, Video, VideoSchedule,
    ARContent, VideoRotationSchedule, ARViewSession, Notification,
    EmailQueue, AuditLog, SystemSettings, StorageConnection, StorageFolder
)

# Список всех моделей для проверки
MODELS = [
    ("users", User),
    ("companies", Company),
    ("projects", Project),
    ("folders", Folder),
    ("clients", Client),
    ("videos", Video),
    ("video_schedules", VideoSchedule),
    ("ar_content", ARContent),
    ("video_rotation_schedules", VideoRotationSchedule),
    ("ar_view_sessions", ARViewSession),
    ("notifications", Notification),
    ("email_queue", EmailQueue),
    ("audit_log", AuditLog),
    ("system_settings", SystemSettings),
    ("storage_connections", StorageConnection),
    ("storage_folders", StorageFolder),
]


def check_model_compliance():
    """Проверяет соответствие всех моделей структуре БД."""
    # Используем синхронный engine для inspector
    # Преобразуем async URL в sync URL для SQLite
    db_url = settings.DATABASE_URL
    if db_url.startswith('sqlite+aiosqlite:///'):
        db_url = db_url.replace('sqlite+aiosqlite:///', 'sqlite:///')
    elif db_url.startswith('sqlite+aiosqlite://'):
        db_url = db_url.replace('sqlite+aiosqlite://', 'sqlite://')
    
    engine = create_engine(db_url, echo=False)
    inspector = inspect(engine)
    
    issues = []
    all_ok = True
    
    print("=" * 80)
    print("ПРОВЕРКА СООТВЕТСТВИЯ МОДЕЛЕЙ И БАЗЫ ДАННЫХ")
    print("=" * 80)
    print()
    
    for table_name, model in MODELS:
        print(f"Проверка таблицы: {table_name}")
        print("-" * 80)
        
        # Получаем колонки из модели
        model_columns = {}
        for column in model.__table__.columns:
            model_columns[column.name] = {
                'type': str(column.type),
                'nullable': column.nullable,
                'default': column.default.arg if column.default else None,
            }
        
        # Получаем колонки из БД
        if not inspector.has_table(table_name):
            print(f"  [ERROR] ТАБЛИЦА НЕ СУЩЕСТВУЕТ В БД!")
            issues.append({
                'table': table_name,
                'issue': 'table_missing',
                'message': f'Таблица {table_name} не существует в базе данных'
            })
            all_ok = False
            print()
            continue
        
        db_columns = {}
        for column in inspector.get_columns(table_name):
            db_columns[column['name']] = {
                'type': str(column['type']),
                'nullable': column['nullable'],
            }
        
        # Проверяем колонки модели в БД
        model_missing = []
        for col_name, col_info in model_columns.items():
            if col_name not in db_columns:
                model_missing.append(col_name)
                issues.append({
                    'table': table_name,
                    'issue': 'column_missing',
                    'column': col_name,
                    'message': f'Колонка {col_name} определена в модели, но отсутствует в БД'
                })
                all_ok = False
        
        # Проверяем лишние колонки в БД (не критично, но стоит отметить)
        db_extra = []
        for col_name in db_columns:
            if col_name not in model_columns:
                db_extra.append(col_name)
        
        # Выводим результаты
        if model_missing:
            print(f"  [ERROR] Отсутствующие колонки в БД: {', '.join(model_missing)}")
        else:
            print(f"  [OK] Все колонки модели присутствуют в БД")
        
        if db_extra:
            print(f"  [WARN] Дополнительные колонки в БД (не в модели): {', '.join(db_extra)}")
        
        print(f"  Модель: {len(model_columns)} колонок")
        print(f"  БД: {len(db_columns)} колонок")
        print()
    
    engine.dispose()
    
    print("=" * 80)
    if all_ok:
        print("[OK] ВСЕ МОДЕЛИ СООТВЕТСТВУЮТ БАЗЕ ДАННЫХ")
    else:
        print("[ERROR] ОБНАРУЖЕНЫ НЕСООТВЕТСТВИЯ")
        print()
        print("СВОДКА ПРОБЛЕМ:")
        print("-" * 80)
        for issue in issues:
            print(f"  • {issue['message']}")
    print("=" * 80)
    
    return issues


if __name__ == "__main__":
    issues = check_model_compliance()
    sys.exit(0 if not issues else 1)
