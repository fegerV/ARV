# Миграции базы данных

Документация по работе с миграциями базы данных в проекте ARV.

## Обзор

Проект использует **Alembic** для управления миграциями базы данных. Alembic - это инструмент миграций для SQLAlchemy, который позволяет версионировать схему базы данных.

## Структура миграций

### Расположение файлов

- **Конфигурация**: `alembic.ini`
- **Скрипты миграций**: `alembic/versions/`
- **Шаблон миграций**: `alembic/script.py.mako`
- **Окружение**: `alembic/env.py`

### Формат имен файлов

Файлы миграций именуются по шаблону:
```
YYYYMMDD_HHMM_<revision>_<description>.py
```

**Пример:**
```
20260125_1200_add_status_to_video_schedules.py
```

## Основные команды

### Применение миграций

```bash
# Применить все миграции до последней версии
alembic upgrade head

# Применить миграции до конкретной версии
alembic upgrade <revision>

# Применить следующую миграцию
alembic upgrade +1
```

### Откат миграций

```bash
# Откатить на одну версию назад
alembic downgrade -1

# Откатить до конкретной версии
alembic downgrade <revision>

# Откатить все миграции
alembic downgrade base
```

### Создание миграций

```bash
# Автоматическое создание миграции на основе изменений моделей
alembic revision --autogenerate -m "Описание изменений"

# Создание пустой миграции (для ручного написания)
alembic revision -m "Описание изменений"
```

### Просмотр информации

```bash
# Текущая версия базы данных
alembic current

# История миграций
alembic history

# История с подробностями
alembic history --verbose

# Показать SQL для миграции (без применения)
alembic upgrade head --sql
```

## Работа с миграциями

### Автоматическое создание миграций

Alembic может автоматически обнаруживать изменения в моделях SQLAlchemy:

```bash
alembic revision --autogenerate -m "Добавлено поле status в таблицу ar_content"
```

**Важно:** Всегда проверяйте автоматически сгенерированные миграции перед применением!

### Ручное создание миграций

Для сложных изменений создайте пустую миграцию:

```bash
alembic revision -m "Сложная миграция данных"
```

Затем отредактируйте файл в `alembic/versions/`:

```python
def upgrade() -> None:
    # Ваш код миграции
    op.add_column('table_name', sa.Column('new_field', sa.String()))
    
    # Миграция данных
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE table_name SET new_field = 'default'")
    )

def downgrade() -> None:
    # Откат изменений
    op.drop_column('table_name', 'new_field')
```

## Конфигурация

### alembic.ini

Основные настройки в `alembic.ini`:

```ini
[alembic]
script_location = alembic
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s
```

### env.py

Файл `alembic/env.py` настраивает подключение к базе данных:

```python
from app.core.config import settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
```

**Важно:** URL базы данных берется из переменных окружения через `settings.DATABASE_URL`.

## Автоматическое применение миграций

### При запуске приложения

Миграции автоматически применяются при старте через `app/core/database.py`:

```python
def init_db_sync() -> None:
    """Initialize database by running Alembic migrations"""
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    command.upgrade(alembic_cfg, "head")
```

### В Docker

В `entrypoint.dev.sh` и `entrypoint.sh` миграции применяются перед запуском:

```bash
echo "Running database migrations..."
alembic upgrade head
```

## Работа с разными базами данных

### SQLite (разработка)

```bash
export DATABASE_URL="sqlite+aiosqlite:///./test_vertex_ar.db"
alembic upgrade head
```

### PostgreSQL (продакшен)

```bash
export DATABASE_URL="postgresql+asyncpg://user:password@host:5432/dbname"
alembic upgrade head
```

## Лучшие практики

### 1. Всегда проверяйте автогенерированные миграции

```bash
alembic revision --autogenerate -m "..." 
# Откройте файл и проверьте изменения
```

### 2. Тестируйте миграции на тестовой базе

```bash
# Создайте тестовую БД
createdb test_db

# Примените миграции
DATABASE_URL="postgresql://..." alembic upgrade head

# Проверьте откат
alembic downgrade -1
alembic upgrade head
```

### 3. Используйте описательные сообщения

```bash
# Хорошо
alembic revision -m "Добавлено поле email в таблицу users"

# Плохо
alembic revision -m "fix"
```

### 4. Не редактируйте примененные миграции

Создайте новую миграцию для исправлений.

### 5. Миграции данных отдельно от схемы

Для больших миграций данных создавайте отдельные миграции:

```python
def upgrade() -> None:
    # 1. Добавить колонку как nullable
    op.add_column('users', sa.Column('new_field', sa.String(), nullable=True))
    
    # 2. Заполнить данные
    connection = op.get_bind()
    connection.execute(sa.text("UPDATE users SET new_field = ..."))
    
    # 3. Сделать NOT NULL (если нужно)
    op.alter_column('users', 'new_field', nullable=False)
```

## Решение проблем

### Проблема: "Target database is not up to date"

**Решение:**
```bash
# Проверьте текущую версию
alembic current

# Примените все миграции
alembic upgrade head
```

### Проблема: Конфликт миграций

**Решение:**
```bash
# Просмотрите историю
alembic history

# Найдите конфликтующую миграцию и разрешите вручную
# Или откатитесь и примените заново
alembic downgrade <revision-before-conflict>
alembic upgrade head
```

### Проблема: Миграция не видит изменения моделей

**Решение:**
1. Убедитесь, что все модели импортированы в `alembic/env.py`:
```python
from app.models import *
```

2. Проверьте, что `target_metadata = Base.metadata` установлен

### Проблема: Ошибка при применении миграции

**Решение:**
```bash
# Просмотрите SQL без применения
alembic upgrade head --sql

# Откатите проблемную миграцию
alembic downgrade -1

# Исправьте миграцию и примените снова
alembic upgrade head
```

## Существующие миграции

Список основных миграций в проекте:

1. `20251217_0206_28cd993514df_initial_schema.py` - Начальная схема БД
2. `20251217_0211_45a7b8c9d1ef_seed_initial_data.py` - Начальные данные
3. `20251218_1959_a24b93e402c7_add_thumbnail_url_field_to_ar_content_.py` - Поле thumbnail_url
4. `20251218_2233_e90dda773ba4_add_marker_fields_to_ar_content_table.py` - Поля маркеров
5. `20251223_1200_comprehensive_ar_content_fix.py` - Исправления AR контента
6. `20251227_1000_create_system_settings.py` - Таблица настроек системы
7. `20260125_1200_add_status_to_video_schedules.py` - Статус для расписания видео
8. `20260125_1201_add_description_to_video_schedules.py` - Описание для расписания
9. `20260125_1202_add_project_id_to_folders.py` - project_id для папок
10. `20260125_1203_add_missing_columns_to_folders.py` - Дополнительные поля папок
11. `20260125_1204_add_missing_columns_to_clients.py` - Дополнительные поля клиентов

## Полезные скрипты

В проекте есть утилиты для работы с миграциями:

- `utilities/check_migration.py`: Проверка состояния миграций
- `utilities/fix_migration.py`: Исправление проблем с миграциями
- `utilities/clear_migrations.py`: Очистка миграций (осторожно!)

## Дополнительные ресурсы

- [Документация Alembic](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Migrations Guide](https://docs.sqlalchemy.org/en/20/core/metadata.html)
