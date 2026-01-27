# Модели данных

Подробное описание моделей данных и схемы базы данных платформы ARV.

## Обзор

Платформа использует SQLAlchemy 2.0 для работы с базой данных. Все модели наследуются от `Base` и используют асинхронные сессии.

## Схема базы данных

### ER-диаграмма связей

```
Users
  │
  └─→ (нет прямой связи)

Companies
  │
  ├─→ Projects (1:N)
  │     │
  │     └─→ ARContent (1:N)
  │           │
  │           ├─→ Videos (1:N)
  │           │     │
  │           │     └─→ VideoSchedules (1:N)
  │           │
  │           └─→ ARViewSessions (1:N)
  │
  └─→ ARContent (1:N, через project)

StorageConnections
  │
  └─→ StorageFolders (1:N)

Notifications
  │
  └─→ (связи с company_id, project_id, ar_content_id)

SystemSettings
  │
  └─→ (независимая таблица)
```

## Основные модели

### User (Пользователи)

**Таблица**: `users`

**Описание**: Пользователи системы (администраторы)

**Поля**:
- `id` (Integer, PK) - Уникальный идентификатор
- `email` (String, Unique, Index) - Email пользователя
- `hashed_password` (String) - SHA-256 хеш пароля
- `full_name` (String) - Полное имя
- `role` (String, default="admin") - Роль пользователя
- `is_active` (Boolean, default=True) - Активен ли пользователь
- `last_login_at` (DateTime, nullable) - Время последнего входа
- `login_attempts` (Integer, default=0) - Количество неудачных попыток входа
- `locked_until` (DateTime, nullable) - Время до разблокировки
- `created_at` (DateTime) - Дата создания
- `updated_at` (DateTime) - Дата обновления

**Индексы**:
- `email` - Уникальный индекс

**Связи**: Нет прямых связей с другими моделями

### Company (Компании)

**Таблица**: `companies`

**Описание**: Компании-клиенты платформы

**Поля**:
- `id` (Integer, PK) - Уникальный идентификатор
- `name` (String(255)) - Название компании
- `slug` (String(255), Unique) - URL-friendly идентификатор
- `contact_email` (String(255), nullable) - Email для связи
- `status` (String(50), default="active") - Статус компании
- `created_at` (DateTime) - Дата создания
- `updated_at` (DateTime) - Дата обновления

**Статусы** (CompanyStatus enum):
- `ACTIVE` - Активная компания
- `INACTIVE` - Неактивная компания

**Связи**:
- `projects` (1:N) - Проекты компании
- `ar_contents` (1:N) - AR-контент компании

**Свойства**:
- `projects_count` - Количество проектов
- `ar_content_count` - Количество AR-контента

### Project (Проекты)

**Таблица**: `projects`

**Описание**: Проекты внутри компаний

**Поля**:
- `id` (Integer, PK) - Уникальный идентификатор
- `company_id` (Integer, FK → companies.id, Index) - ID компании
- `name` (String(255)) - Название проекта
- `status` (String(50), default="active") - Статус проекта
- `created_at` (DateTime) - Дата создания
- `updated_at` (DateTime) - Дата обновления

**Статусы** (ProjectStatus enum):
- `ACTIVE` - Активный проект
- `INACTIVE` - Неактивный проект
- `ARCHIVED` - Архивированный проект

**Связи**:
- `company` (N:1) - Компания-владелец
- `ar_contents` (1:N) - AR-контент проекта

**Индексы**:
- `ix_project_company_name` - Уникальность имени в рамках компании

**Свойства**:
- `ar_content_count` - Количество AR-контента

### ARContent (AR-контент)

**Таблица**: `ar_content`

**Описание**: Основная модель AR-контента с информацией о заказчике

**Поля**:
- `id` (Integer, PK) - Уникальный идентификатор
- `project_id` (Integer, FK → projects.id, Index) - ID проекта
- `company_id` (Integer, FK → companies.id) - ID компании
- `active_video_id` (Integer, FK → videos.id, nullable) - ID активного видео
- `unique_id` (String(36), Unique) - UUID для публичных ссылок
- `order_number` (String(50)) - Номер заказа
- `customer_name` (String(255), nullable) - Имя заказчика
- `customer_phone` (String(50), nullable) - Телефон заказчика
- `customer_email` (String(255), nullable) - Email заказчика
- `duration_years` (Integer, default=1) - Длительность подписки (1, 3 или 5 лет)
- `views_count` (Integer, default=0) - Количество просмотров
- `status` (String(50), default="pending") - Статус контента
- `content_metadata` (JSON/JSONB, nullable) - Дополнительные метаданные
- `photo_path` (String(500), nullable) - Путь к фото
- `photo_url` (String(500), nullable) - URL фото
- `thumbnail_url` (String(500), nullable) - URL превью
- `video_path` (String(500), nullable) - Путь к видео (deprecated)
- `video_url` (String(500), nullable) - URL видео (deprecated)
- `qr_code_path` (String(500), nullable) - Путь к QR-коду
- `qr_code_url` (String(500), nullable) - URL QR-кода
- `marker_path` (String(500), nullable) - Путь к маркеру
- `marker_url` (String(500), nullable) - URL маркера
- `marker_status` (String(50), default="pending") - Статус генерации маркера
- `marker_metadata` (JSON/JSONB, nullable) - Метаданные маркера
- `rotation_state` (Integer, nullable) - Текущее состояние ротации видео
- `created_at` (DateTime) - Дата создания
- `updated_at` (DateTime) - Дата обновления

**Статусы** (ArContentStatus enum):
- `PENDING` - Ожидает обработки
- `ACTIVE` - Активен
- `ARCHIVED` - Архивирован

**Ограничения**:
- `check_duration_years` - duration_years IN (1, 3, 5)
- `check_views_count_non_negative` - views_count >= 0

**Индексы**:
- `ix_ar_content_project_order` - Уникальность order_number в рамках проекта
- `ix_ar_content_company_project` - Индекс по company_id и project_id
- `ix_ar_content_created_at` - Индекс по дате создания
- `ix_ar_content_status` - Индекс по статусу
- `ix_ar_content_unique_id` - Индекс по unique_id

**Связи**:
- `project` (N:1) - Проект
- `company` (N:1) - Компания
- `videos` (1:N) - Видео контента
- `active_video` (N:1) - Активное видео

**Свойства**:
- `public_link` - Публичная ссылка для AR viewer
- `qr_code_path_property` - Путь к QR-коду

**Методы**:
- `validate_email()` - Валидация email заказчика

### Video (Видео)

**Таблица**: `videos`

**Описание**: Видео файлы для AR-контента

**Поля**:
- `id` (Integer, PK) - Уникальный идентификатор
- `ar_content_id` (Integer, FK → ar_content.id) - ID AR-контента
- `filename` (String(255)) - Имя файла
- `video_path` (String(500), nullable) - Путь к видео
- `video_url` (String(500), nullable) - URL видео
- `thumbnail_path` (String(500), nullable) - Путь к превью
- `preview_url` (String(500), nullable) - URL превью
- `duration` (Integer, nullable) - Длительность в секундах
- `width` (Integer, nullable) - Ширина видео
- `height` (Integer, nullable) - Высота видео
- `size_bytes` (Integer, nullable) - Размер в байтах
- `mime_type` (String(100), nullable) - MIME тип
- `status` (String(50), default="uploaded") - Статус видео
- `is_active` (Boolean, default=False) - Активно ли видео
- `rotation_type` (String(20), default="none") - Тип ротации
- `rotation_order` (Integer, default=0) - Порядок в ротации
- `subscription_end` (DateTime, nullable) - Дата окончания подписки
- `created_at` (DateTime) - Дата создания
- `updated_at` (DateTime) - Дата обновления

**Статусы** (VideoStatus enum):
- `UPLOADED` - Загружено
- `PROCESSING` - Обрабатывается
- `READY` - Готово
- `FAILED` - Ошибка

**Типы ротации**:
- `none` - Без ротации (фиксированное видео)
- `sequential` - Последовательная ротация
- `cyclic` - Циклическая ротация

**Связи**:
- `ar_content` (N:1) - AR-контент
- `schedules` (1:N) - Расписание видео

### VideoSchedule (Расписание видео)

**Таблица**: `video_schedules`

**Описание**: Временные окна для показа видео

**Поля**:
- `id` (Integer, PK) - Уникальный идентификатор
- `video_id` (Integer, FK → videos.id, CASCADE) - ID видео
- `start_time` (DateTime) - Время начала показа
- `end_time` (DateTime) - Время окончания показа
- `status` (String(20), default="active") - Статус расписания
- `description` (String(500), nullable) - Описание расписания
- `created_at` (DateTime) - Дата создания
- `updated_at` (DateTime) - Дата обновления

**Ограничения**:
- `check_schedule_time_range` - start_time <= end_time

**Статусы**:
- `active` - Активно
- `expired` - Истекло

**Связи**:
- `video` (N:1) - Видео

### Notification (Уведомления)

**Таблица**: `notifications`

**Описание**: Уведомления системы

**Поля**:
- `id` (Integer, PK) - Уникальный идентификатор
- `company_id` (Integer, nullable) - ID компании
- `project_id` (Integer, nullable) - ID проекта
- `ar_content_id` (Integer, nullable) - ID AR-контента
- `notification_type` (String(50)) - Тип уведомления
- `email_sent` (Boolean, default=False) - Отправлено ли по email
- `email_sent_at` (DateTime, nullable) - Время отправки email
- `email_error` (Text, nullable) - Ошибка отправки email
- `telegram_sent` (Boolean, default=False) - Отправлено ли в Telegram
- `telegram_sent_at` (DateTime, nullable) - Время отправки в Telegram
- `telegram_error` (Text, nullable) - Ошибка отправки в Telegram
- `subject` (String(500), nullable) - Тема уведомления
- `message` (Text, nullable) - Текст уведомления
- `notification_metadata` (JSON/JSONB, default={}) - Метаданные
- `created_at` (DateTime) - Дата создания

**Связи**: Нет прямых связей (используются ID)

### StorageConnection (Подключения к хранилищу)

**Таблица**: `storage_connections`

**Описание**: Подключения к различным хранилищам

**Поля**:
- `id` (Integer, PK) - Уникальный идентификатор
- `name` (String(255)) - Название подключения
- `provider` (String(50)) - Тип провайдера (local_disk, s3, yandex)
- `base_path` (String(500)) - Базовый путь
- `is_active` (Boolean, default=True) - Активно ли подключение
- `is_default` (Boolean, default=False) - По умолчанию ли
- `connection_config` (JSON/JSONB, nullable) - Конфигурация подключения
- `created_at` (DateTime) - Дата создания
- `updated_at` (DateTime) - Дата обновления

**Связи**:
- `folders` (1:N) - Папки хранилища

### StorageFolder (Папки хранилища)

**Таблица**: `storage_folders`

**Описание**: Папки в хранилище

**Поля**:
- `id` (Integer, PK) - Уникальный идентификатор
- `storage_connection_id` (Integer, FK → storage_connections.id) - ID подключения
- `project_id` (Integer, FK → projects.id, nullable) - ID проекта
- `name` (String(255)) - Название папки
- `path` (String(500)) - Путь к папке
- `created_at` (DateTime) - Дата создания
- `updated_at` (DateTime) - Дата обновления

**Связи**:
- `storage_connection` (N:1) - Подключение к хранилищу
- `project` (N:1) - Проект

### SystemSettings (Настройки системы)

**Таблица**: `system_settings`

**Описание**: Настройки системы

**Поля**:
- `id` (Integer, PK) - Уникальный идентификатор
- `key` (String(255), Unique) - Ключ настройки
- `value` (Text) - Значение настройки
- `value_type` (String(50)) - Тип значения (string, integer, boolean, json)
- `category` (String(50)) - Категория настройки
- `description` (Text, nullable) - Описание
- `is_public` (Boolean, default=False) - Публичная ли настройка
- `created_at` (DateTime) - Дата создания
- `updated_at` (DateTime) - Дата обновления

**Категории**:
- `general` - Общие настройки
- `storage` - Настройки хранилища
- `notifications` - Настройки уведомлений
- `api` - Настройки API
- `integrations` - Настройки интеграций
- `ar` - Настройки AR

### ARViewSession (Сессии просмотра AR)

**Таблица**: `ar_view_sessions`

**Описание**: Сессии просмотра AR-контента

**Поля**:
- `id` (Integer, PK) - Уникальный идентификатор
- `ar_content_id` (Integer, FK → ar_content.id) - ID AR-контента
- `session_id` (String(255), Unique) - Уникальный ID сессии
- `ip_address` (String(50), nullable) - IP адрес
- `user_agent` (String(500), nullable) - User agent
- `view_duration` (Integer, nullable) - Длительность просмотра в секундах
- `session_metadata` (JSON/JSONB, nullable) - Метаданные сессии
- `created_at` (DateTime) - Дата создания
- `ended_at` (DateTime, nullable) - Дата окончания

**Связи**:
- `ar_content` (N:1) - AR-контент

### Client (Клиенты)

**Таблица**: `clients`

**Описание**: Клиенты компаний

**Поля**:
- `id` (Integer, PK) - Уникальный идентификатор
- `company_id` (Integer, FK → companies.id) - ID компании
- `name` (String(255)) - Имя клиента
- `email` (String(255), nullable) - Email клиента
- `phone` (String(50), nullable) - Телефон клиента
- `created_at` (DateTime) - Дата создания
- `updated_at` (DateTime) - Дата обновления

**Связи**:
- `company` (N:1) - Компания

### Folder (Папки проектов)

**Таблица**: `folders`

**Описание**: Папки для организации проектов

**Поля**:
- `id` (Integer, PK) - Уникальный идентификатор
- `project_id` (Integer, FK → projects.id, nullable) - ID проекта
- `name` (String(255)) - Название папки
- `parent_id` (Integer, FK → folders.id, nullable) - ID родительской папки
- `created_at` (DateTime) - Дата создания
- `updated_at` (DateTime) - Дата обновления

**Связи**:
- `project` (N:1) - Проект
- `parent` (N:1, self-reference) - Родительская папка

## Enums

### CompanyStatus

```python
class CompanyStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
```

### ProjectStatus

```python
class ProjectStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
```

### ArContentStatus

```python
class ArContentStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    ARCHIVED = "archived"
```

### VideoStatus

```python
class VideoStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
```

## Индексы

### Основные индексы

1. **users.email** - Уникальный индекс для быстрого поиска пользователей
2. **companies.slug** - Уникальный индекс для URL-friendly идентификаторов
3. **projects.company_id** - Индекс для фильтрации проектов по компании
4. **ar_content.project_id** - Индекс для фильтрации контента по проекту
5. **ar_content.unique_id** - Уникальный индекс для публичных ссылок
6. **ar_content.status** - Индекс для фильтрации по статусу
7. **videos.ar_content_id** - Индекс для связи с AR-контентом
8. **video_schedules.video_id** - Индекс для связи с видео

### Составные индексы

1. **ix_project_company_name** - Уникальность имени проекта в рамках компании
2. **ix_ar_content_project_order** - Уникальность номера заказа в рамках проекта
3. **ix_ar_content_company_project** - Индекс по компании и проекту

## Ограничения (Constraints)

1. **check_duration_years** - ARContent.duration_years IN (1, 3, 5)
2. **check_views_count_non_negative** - ARContent.views_count >= 0
3. **check_schedule_time_range** - VideoSchedule.start_time <= end_time

## Каскадные операции

### CASCADE DELETE

- `projects` → `ar_contents` (при удалении проекта удаляется контент)
- `ar_contents` → `videos` (при удалении контента удаляются видео)
- `videos` → `video_schedules` (при удалении видео удаляется расписание)
- `companies` → `projects` (при удалении компании удаляются проекты)

## Миграции

Все изменения схемы БД выполняются через Alembic миграции:

- Файлы миграций: `alembic/versions/`
- Формат имен: `YYYYMMDD_HHMM_<revision>_<description>.py`
- Применение: `alembic upgrade head`
- Откат: `alembic downgrade -1`

## Работа с моделями

### Создание записи

```python
from app.models import Company
from app.core.database import get_db

async def create_company(db: AsyncSession, name: str):
    company = Company(
        name=name,
        slug=slugify(name),
        status=CompanyStatus.ACTIVE
    )
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company
```

### Получение записи

```python
from sqlalchemy import select

async def get_company(db: AsyncSession, company_id: int):
    result = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    return result.scalar_one_or_none()
```

### Обновление записи

```python
async def update_company(db: AsyncSession, company_id: int, name: str):
    company = await db.get(Company, company_id)
    if company:
        company.name = name
        await db.commit()
        await db.refresh(company)
    return company
```

### Удаление записи

```python
async def delete_company(db: AsyncSession, company_id: int):
    company = await db.get(Company, company_id)
    if company:
        await db.delete(company)
        await db.commit()
    return company
```

## Best Practices

1. **Всегда используйте async сессии** для работы с БД
2. **Используйте relationships** для навигации между моделями
3. **Валидируйте данные** перед сохранением
4. **Используйте транзакции** для сложных операций
5. **Обрабатывайте ошибки** при работе с БД
6. **Используйте индексы** для часто запрашиваемых полей
7. **Документируйте связи** между моделями
