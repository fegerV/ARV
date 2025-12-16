# Документация базы данных ARVlite

## Структура базы данных

### ER-диаграмма (текстовое представление)

```
┌─────────────────┐    ┌─────────────────┐    ┌──────────────────┐
│   companies     │    │    projects     │    │   ar_content     │
│                 │    │                  │
│ id (PK)         │───→│ company_id (FK) │───→│ project_id (FK)  │
│ name            │    │ id (PK)         │    │ id (PK)          │
│ slug            │    │ name            │    │ unique_id        │
│ contact_email   │    │ status          │    │ order_number     │
│ status          │    │ created_at      │    │ customer_name    │
│ created_at      │    │ updated_at      │    │ customer_phone   │
│ updated_at      │    │                 │    │ customer_email   │
└─────────────────┘    └─────────────────┘    │ duration_years   │
                                              │ views_count      │
                                              │ status           │
                                              │ photo_path       │
                                              │ video_path       │
                                              │ qr_code_path     │
                                              │ created_at       │
                                              │ updated_at       │
                                              └──────────────────┘
                                                       │
                                                       │
                                                       ▼
                                               ┌──────────────────┐
                                               │     videos       │
                                               │                  │
                                               │ id (PK)          │
                                               │ ar_content_id (FK)│
                                               │ filename         │
                                               │ video_path       │
                                               │ thumbnail_path   │
                                               │ status           │
                                               │ is_active        │
                                               │ rotation_type    │
                                               │ rotation_order   │
                                               │ created_at       │
                                               │ updated_at       │
                                               └──────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌──────────────────┐
│     users       │    │   clients       │    │  video_schedules │
│                 │    │                  │
│ id (PK)         │    │ id (PK)         │    │ id (PK)          │
│ email           │    │ company_id (FK) │    │ video_id (FK)    │
│ hashed_password │    │ name            │    │ start_time       │
│ full_name       │    │ phone           │    │ end_time         │
│ role            │    │ email           │    │ status           │
│ is_active       │    │ address         │    │ created_at       │
│ created_at      │    │ created_at      │    │ updated_at       │
│ updated_at      │    │ updated_at      │    └──────────────────┘
└─────────────────┘    └─────────────────┘

┌─────────────────────────┐    ┌─────────────────────────┐
│   video_rotation_schedules│    │   ar_view_sessions      │
│                         │    │                         │
│ id (PK)                 │    │ id (PK)                 │
│ ar_content_id (FK)      │    │ ar_content_id (FK)      │
│ rotation_type           │    │ project_id (FK)         │
│ time_of_day             │    │ company_id (FK)         │
│ day_of_week             │    │ session_id             │
│ day_of_month            │    │ user_agent             │
│ cron_expression         │    │ device_type            │
│ video_sequence          │    │ browser                │
│ current_index           │    │ os                     │
│ is_active               │    │ ip_address             │
│ last_rotation_at        │    │ country                │
│ next_rotation_at        │    │ city                   │
│ created_at              │    │ duration_seconds       │
│ updated_at              │    │ tracking_quality       │
└─────────────────────────┘    │ video_played           │
                              │ created_at             │
┌─────────────────────────┐    │ updated_at             │
│      folders            │    └─────────────────────────┘
│                         │
│ id (PK)                 │    ┌─────────────────────────┐
│ project_id (FK)         │    │      notifications      │
│ name                    │    │                         │
│ description             │    │ id (PK)                 │
│ parent_id               │    │ company_id              │
│ folder_path             │    │ project_id              │
│ is_active               │    │ ar_content_id           │
│ sort_order              │    │ notification_type       │
│ created_at              │    │ email_sent              │
│ updated_at              │    │ email_sent_at           │
└─────────────────────────┘    │ email_error             │
                              │ telegram_sent           │
┌─────────────────────────┐    │ telegram_sent_at        │
│      storage            │    │ telegram_error          │
│                         │    │ subject                 │
│ id (PK)                 │    │ message                 │
│ name                    │    │ created_at              │
│ provider                │    └─────────────────────────┘
│ base_path               │
│ is_default              │    ┌─────────────────────────┐
│ is_active               │    │      email_queue        │
│ last_tested_at          │    │                         │
│ test_status             │    │ id (PK)                 │
│ test_error              │    │ recipient_to            │
│ metadata                │    │ subject                 │
│ created_at              │    │ body                    │
│ updated_at              │    │ html                    │
│ created_by              │    │ status                  │
└─────────────────────────┘    │ attempts                │
                              │ max_attempts            │
┌─────────────────────────┐    │ last_error              │
│      audit_log          │    │ priority                │
│                         │    │ scheduled_at            │
│ id (PK)                 │    │ created_at              │
│ entity_type             │    │ updated_at              │
│ entity_id               │    │ sent_at                 │
│ action                  │    └─────────────────────────┘
│ changes                 │
│ field_name              │
│ actor_id                │
│ actor_email             │
│ actor_ip                │
│ user_agent              │
│ session_id              │
│ request_id              │
│ created_at              │
└─────────────────────────┘
```

## Описание таблиц

### 1. users
Таблица пользователей системы

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | Integer | PRIMARY KEY, INDEX | Уникальный идентификатор пользователя |
| email | String | UNIQUE, INDEX, NOT NULL | Email пользователя |
| hashed_password | String | NOT NULL | Хэшированный пароль |
| full_name | String | NOT NULL | Полное имя пользователя |
| role | String | DEFAULT 'admin', NOT NULL | Роль пользователя |
| is_active | Boolean | DEFAULT true, NOT NULL | Статус активности |
| last_login_at | DateTime | TIMEZONE | Время последнего входа |
| created_at | DateTime | DEFAULT now(), NOT NULL | Время создания |
| updated_at | DateTime | DEFAULT now(), ON UPDATE now(), NOT NULL | Время последнего обновления |
| login_attempts | Integer | DEFAULT 0, NOT NULL | Количество попыток входа |
| locked_until | DateTime | TIMEZONE | Время до которого пользователь заблокирован |

**Индексы:**
- `ix_users_email` - уникальный индекс на email
- `ix_users_id` - первичный индекс на id

### 2. companies
Таблица компаний

| Поле | Тип | Ограничения | Описание |
|------|-------------|----------|
| id | Integer | PRIMARY KEY, INDEX | Уникальный идентификатор компании |
| name | String(255) | NOT NULL | Название компании |
| slug | String(255) | NOT NULL | URL-дружественное имя |
| contact_email | String(255) | | Контактный email |
| status | String(50) | DEFAULT 'ACTIVE', NOT NULL | Статус компании |
| created_at | DateTime | DEFAULT utcnow, NOT NULL | Время создания |
| updated_at | DateTime | DEFAULT utcnow, ON UPDATE utcnow, NOT NULL | Время последнего обновления |

**Индексы:**
- `ix_companies_id` - первичный индекс на id

**Связи:**
- `projects` - связь один-ко-многим (CASCADE DELETE)
- `ar_contents` - связь один-ко-многим (CASCADE DELETE)

### 3. projects
Таблица проектов

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | Integer | PRIMARY KEY, INDEX | Уникальный идентификатор проекта |
| name | String(255) | NOT NULL | Название проекта |
| status | String(50) | DEFAULT 'ACTIVE', NOT NULL | Статус проекта |
| company_id | Integer | FOREIGN KEY, INDEX, NOT NULL | Идентификатор компании |
| created_at | DateTime | DEFAULT utcnow, NOT NULL | Время создания |
| updated_at | DateTime | DEFAULT utcnow, ON UPDATE utcnow, NOT NULL | Время последнего обновления |

**Индексы:**
- `ix_projects_id` - первичный индекс на id
- `ix_projects_company_id` - индекс на company_id
- `ix_project_company_name` - уникальный индекс на (company_id, name)

**Связи:**
- `company` - связь многие-к-одному (ForeignKey: companies.id)
- `ar_contents` - связь один-ко-многим (CASCADE DELETE)

### 4. ar_content
Таблица AR-контента

| Поле | Тип | Ограничения | Описание |
|------|-------------|----------|
| id | Integer | PRIMARY KEY, INDEX | Уникальный идентификатор AR-контента |
| project_id | Integer | FOREIGN KEY, INDEX, NOT NULL | Идентификатор проекта |
| company_id | Integer | FOREIGN KEY, NOT NULL | Идентификатор компании |
| active_video_id | Integer | FOREIGN KEY | Идентификатор активного видео |
| unique_id | UUID | DEFAULT uuid4, UNIQUE, NOT NULL | Уникальный UUID для публичных ссылок |
| order_number | String(50) | NOT NULL | Номер заказа |
| customer_name | String(255) | | Имя клиента |
| customer_phone | String(50) | | Телефон клиента |
| customer_email | String(255) | Email клиента |
| duration_years | Integer | DEFAULT 1, NOT NULL | Продолжительность в годах |
| views_count | Integer | DEFAULT 0, NOT NULL | Количество просмотров |
| status | String(50) | DEFAULT 'PENDING', NOT NULL | Статус контента |
| content_metadata | JSON/JSONB | | Метаданные контента |
| photo_path | String(500) | Путь к фото |
| photo_url | String(500) | URL фото |
| video_path | String(500) | | Путь к видео |
| video_url | String(500) | | URL видео |
| qr_code_path | String(500) | | Путь к QR-коду |
| qr_code_url | String(500) | | URL QR-кода |
| created_at | DateTime | DEFAULT utcnow, NOT NULL | Время создания |
| updated_at | DateTime | DEFAULT utcnow, ON UPDATE utcnow, NOT NULL | Время последнего обновления |

**Ограничения:**
- `ix_ar_content_project_order` - уникальный индекс на (project_id, order_number)
- `check_duration_years` - проверка (1, 3, 5)
- `check_views_count_non_negative` - проверка >= 0

**Связи:**
- `project` - связь многие-к-одному (ForeignKey: projects.id)
- `company` - связь многие-к-одному (ForeignKey: companies.id)
- `videos` - связь один-ко-многим (CASCADE DELETE)
- `active_video` - связь многие-к-одному (ForeignKey: videos.id)

### 5. videos
Таблица видео

| Поле | Тип | Ограничения | Описание |
|------|-------------|----------|
| id | Integer | PRIMARY KEY, INDEX | Уникальный идентификатор видео |
| ar_content_id | Integer | FOREIGN KEY, NOT NULL | Идентификатор AR-контента |
| filename | String(255) | NOT NULL | Имя файла |
| video_path | String(500) | | Путь к видео |
| video_url | String(500) | | URL видео |
| thumbnail_path | String(500) | Путь к миниатюре |
| thumbnail_url | String(500) | URL миниатюры |
| preview_url | String(500) | | URL превью |
| duration | Integer | | Длительность в секундах |
| width | Integer | | Ширина |
| height | Integer | | Высота |
| size_bytes | Integer | | Размер в байтах |
| mime_type | String(100) | | MIME-тип |
| status | String(50) | DEFAULT 'UPLOADED', NOT NULL | Статус видео |
| is_active | Boolean | DEFAULT false, NOT NULL | Активность |
| rotation_type | String(20) | DEFAULT 'none', NOT NULL | Тип ротации |
| rotation_order | Integer | DEFAULT 0, NOT NULL | Порядок ротации |
| subscription_end | DateTime | | Окончание подписки |
| created_at | DateTime | DEFAULT utcnow, NOT NULL | Время создания |
| updated_at | DateTime | DEFAULT utcnow, ON UPDATE utcnow, NOT NULL | Время последнего обновления |

**Связи:**
- `ar_content` - связь многие-к-одному (ForeignKey: ar_content.id)
- `schedules` - связь один-ко-многим (CASCADE DELETE)

### 6. video_schedules
Таблица расписаний видео

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | Integer | PRIMARY KEY, INDEX | Уникальный идентификатор расписания |
| video_id | Integer | FOREIGN KEY, NOT NULL | Идентификатор видео |
| start_time | DateTime | NOT NULL | Время начала |
| end_time | DateTime | NOT NULL | Время окончания |
| status | String(20) | DEFAULT 'active' | Статус расписания |
| description | String(500) | | Описание расписания |
| created_at | DateTime | DEFAULT utcnow, NOT NULL | Время создания |
| updated_at | DateTime | DEFAULT utcnow, ON UPDATE utcnow, NOT NULL | Время последнего обновления |

**Ограничения:**
- `check_schedule_time_range` - проверка start_time <= end_time

**Связи:**
- `video` - связь многие-к-одному (ForeignKey: videos.id, ON DELETE CASCADE)

### 7. video_rotation_schedules
Таблица расписаний ротации видео

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | Integer | PRIMARY KEY, INDEX | Уникальный идентификатор расписания ротации |
| ar_content_id | Integer | FOREIGN KEY, NOT NULL | Идентификатор AR-контента |
| rotation_type | String(50) | NOT NULL | Тип ротации |
| time_of_day | Time | Время суток |
| day_of_week | Integer | | День недели |
| day_of_month | Integer | | День месяца |
| cron_expression | String(100) | | Выражение CRON |
| video_sequence | ARRAY(Integer) | | Последовательность видео |
| current_index | Integer | DEFAULT 0 | Текущий индекс |
| is_active | Integer | DEFAULT 1 | Активность |
| last_rotation_at | DateTime | | Время последней ротации |
| next_rotation_at | DateTime | | Время следующей ротации |
| created_at | DateTime | DEFAULT utcnow, NOT NULL | Время создания |
| updated_at | DateTime | DEFAULT utcnow, ON UPDATE utcnow, NOT NULL | Время последнего обновления |

**Связи:**
- `ar_content` - связь многие-к-одному (ForeignKey: ar_content.id)

### 8. ar_view_sessions
Таблица сессий просмотра AR

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | Integer | PRIMARY KEY, INDEX | Уникальный идентификатор сессии |
| ar_content_id | Integer | FOREIGN KEY, NOT NULL | Идентификатор AR-контента |
| project_id | Integer | FOREIGN KEY, NOT NULL | Идентификатор проекта |
| company_id | Integer | FOREIGN KEY, NOT NULL | Идентификатор компании |
| session_id | UUID | | UUID сессии |
| user_agent | String | | User agent |
| device_type | String(50) | | Тип устройства |
| browser | String(100) | | Браузер |
| os | String(100) | | Операционная система |
| ip_address | String(64) | | IP-адрес |
| country | String(100) | | Страна |
| city | String(100) | | Город |
| duration_seconds | Integer | | Длительность в секундах |
| tracking_quality | String(50) | | Качество отслеживания |
| video_played | Boolean | DEFAULT false | Видео воспроизведено |
| created_at | DateTime | DEFAULT utcnow, NOT NULL | Время создания |
| updated_at | DateTime | DEFAULT utcnow, ON UPDATE utcnow, NOT NULL | Время последнего обновления |

**Связи:**
- `ar_content` - связь многие-к-одному (ForeignKey: ar_content.id)
- `project` - связь многие-к-одному (ForeignKey: projects.id)
- `company` - связь многие-к-одному (ForeignKey: companies.id)

### 9. notifications
Таблица уведомлений

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | Integer | PRIMARY KEY | Уникальный идентификатор уведомления |
| company_id | Integer | | Идентификатор компании |
| project_id | Integer | | Идентификатор проекта |
| ar_content_id | Integer | | Идентификатор AR-контента |
| notification_type | String(50) | NOT NULL | Тип уведомления |
| email_sent | Boolean | DEFAULT false | Email отправлен |
| email_sent_at | DateTime | Время отправки email |
| email_error | Text | | Ошибка email |
| telegram_sent | Boolean | DEFAULT false | Telegram отправлен |
| telegram_sent_at | DateTime | | Время отправки Telegram |
| telegram_error | Text | | Ошибка Telegram |
| subject | String(500) | | Тема |
| message | Text | | Сообщение |
| metadata | JSON/JSONB | DEFAULT {} | Метаданные |
| created_at | DateTime | DEFAULT utcnow | Время создания |

### 10. email_queue
Таблица очереди email

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | Integer | PRIMARY KEY | Уникальный идентификатор |
| recipient_to | String(255) | NOT NULL | Получатель |
| recipient_cc | String(255) | | Копия |
| recipient_bcc | String(255) | | Скрытая копия |
| subject | String(500) | NOT NULL | Тема |
| body | Text | NOT NULL | Тело письма |
| html | Text | | HTML-версия |
| template_id | String(100) | | ID шаблона |
| variables | JSON/JSONB | DEFAULT {} | Переменные |
| status | String(50) | DEFAULT 'pending' | Статус |
| attempts | Integer | DEFAULT 0 | Попытки отправки |
| max_attempts | Integer | DEFAULT 3 | Максимальное количество попыток |
| last_error | Text | | Последняя ошибка |
| priority | Integer | DEFAULT 5 | Приоритет (1-10) |
| scheduled_at | DateTime | | Запланированное время |
| created_at | DateTime | DEFAULT utcnow | Время создания |
| updated_at | DateTime | DEFAULT utcnow, ON UPDATE utcnow | Время обновления |
| sent_at | DateTime | | Время отправки |

### 11. audit_log
Таблица аудита

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | Integer | PRIMARY KEY | Уникальный идентификатор |
| entity_type | String(100) | NOT NULL | Тип сущности |
| entity_id | Integer | NOT NULL | ID сущности |
| action | String(100) | NOT NULL | Действие |
| changes | JSON/JSONB | DEFAULT {} | Изменения |
| field_name | String(100) | Имя поля |
| actor_id | Integer | FOREIGN KEY | ID актора |
| actor_email | String(255) | | Email актора |
| actor_ip | String(64) | | IP актора |
| user_agent | Text | User agent |
| session_id | String(255) | | ID сессии |
| request_id | String(255) | | ID запроса |
| created_at | DateTime | DEFAULT utcnow, NOT NULL | Время создания |

**Связи:**
- `actor` - связь многие-к-одному (ForeignKey: users.id)

### 12. clients
Таблица клиентов

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | Integer | PRIMARY KEY | Уникальный идентификатор |
| company_id | Integer | FOREIGN KEY, NOT NULL | Идентификатор компании |
| name | String(255) | NOT NULL | Имя клиента |
| phone | String(50) | | Телефон |
| email | String(255) | | Email |
| address | String(500) | | Адрес |
| notes | String(1000) | | Заметки |
| is_active | String(50) | DEFAULT 'active' | Активность |
| created_at | DateTime | DEFAULT utcnow | Время создания |
| updated_at | DateTime | DEFAULT utcnow, ON UPDATE utcnow | Время обновления |

**Связи:**
- `company` - связь многие-к-одному (ForeignKey: companies.id)

### 13. folders
Таблица папок

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | Integer | PRIMARY KEY | Уникальный идентификатор |
| project_id | Integer | FOREIGN KEY, NOT NULL | Идентификатор проекта |
| name | String(255) | NOT NULL | Имя папки |
| description | Text | | Описание |
| parent_id | Integer | FOREIGN KEY | Родительская папка |
| folder_path | String(500) | | Путь к папке |
| is_active | String(50) | DEFAULT 'active' | Активность |
| sort_order | Integer | DEFAULT 0 | Порядок сортировки |
| created_at | DateTime | DEFAULT utcnow | Время создания |
| updated_at | DateTime | DEFAULT utcnow, ON UPDATE utcnow | Время обновления |

**Связи:**
- `project` - связь многие-к-одному (ForeignKey: projects.id)
- `parent` - связь многие-к-одному (ForeignKey: folders.id)

### 14. storage_connections
Таблица подключений хранилищ

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | Integer | PRIMARY KEY | Уникальный идентификатор |
| name | String(255) | UNIQUE, NOT NULL | Имя подключения |
| provider | String(50) | DEFAULT 'local_disk', NOT NULL | Провайдер |
| base_path | String(500) | NOT NULL | Базовый путь |
| is_default | Boolean | DEFAULT false | По умолчанию |
| is_active | Boolean | DEFAULT true | Активность |
| last_tested_at | DateTime | | Время последнего теста |
| test_status | String(50) | | Статус теста |
| test_error | Text | | Ошибка теста |
| metadata | JSON/JSONB | DEFAULT {} | Метаданные |
| created_at | DateTime | DEFAULT utcnow | Время создания |
| updated_at | DateTime | DEFAULT utcnow, ON UPDATE utcnow | Время обновления |
| created_by | Integer | Создан пользователем |

### 15. storage_folders
Таблица папок хранилища

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| id | Integer | PRIMARY KEY | Уникальный идентификатор |
| company_id | Integer | FOREIGN KEY | Идентификатор компании |
| name | String(255) | NOT NULL | Имя папки |
| path | String(500) | NOT NULL | Путь |
| folder_type | String(50) | | Тип папки |
| files_count | Integer | DEFAULT 0 | Количество файлов |
| total_size_bytes | BigInteger | DEFAULT 0 | Общий размер в байтах |
| created_at | DateTime | DEFAULT utcnow | Время создания |
| updated_at | DateTime | DEFAULT utcnow, ON UPDATE utcnow | Время обновления |

## Ключевые связи

### Основные связи
- `companies` → `projects` (один-ко-многим): компания может иметь множество проектов
- `projects` → `ar_content` (один-ко-многим): проект может содержать множество AR-контентов
- `ar_content` → `videos` (один-ко-многим): AR-контент может содержать множество видео
- `ar_content` → `ar_view_sessions` (один-ко-многим): AR-контент может иметь множество сессий просмотра
- `ar_content` → `video_rotation_schedules` (один-ко-многим): AR-контент может иметь расписания ротации
- `videos` → `video_schedules` (один-ко-многим): видео может иметь множество расписаний

### Связи с пользователями
- `users` → `audit_log` (один-ко-многим): пользователь может быть инициатором множества записей аудита
- `companies` → `clients` (один-ко-многим): компания может иметь множество клиентов
- `projects` → `folders` (один-ко-многим): проект может содержать множество папок

## Alembic миграции

### Основы работы с миграциями

Alembic - это инструмент управления схемой базы данных для SQLAlchemy. Он позволяет создавать, применять и откатывать миграции для управления структурой базы данных.

### Конфигурация Alembic

- **Файл конфигурации**: `alembic.ini`
- **Папка миграций**: `alembic/versions/`
- **Шаблон миграций**: `alembic/script.py.mako`
- **Конфигурационный файл**: `alembic/env.py`

### Структура миграций

Миграции находятся в папке `alembic/versions/` и именуются по формату: `{дата_время}_{ревизия}_{описание}.py`

Пример: `20251217_0206_28cd993514df_initial_schema.py`

## Создание новых миграций

Для создания новой миграции используйте команду:

```bash
alembic revision -m "описание миграции"
```

Это создаст новый файл миграции в `alembic/versions/` с шаблоном, который нужно заполнить.

Для автоматической генерации миграции на основе изменений в моделях:

```bash
alembic revision --autogenerate -m "описание миграции"
```

## Применение миграций

Для применения всех непримененных миграций:

```bash
alembic upgrade head
```

Для применения конкретной миграции:

```bash
alembic upgrade <revision_id>
```

Для применения следующей миграции:

```bash
alembic upgrade +1
```

## Откат миграций

Для отката последней миграции:

```bash
alembic downgrade -1
```

Для отката до конкретной миграции:

```bash
alembic downgrade <revision_id>
```

Для отката всех миграций:

```bash
alembic downgrade base
```

## Seed данные

Приложение включает в себя seed-данные для начальной настройки базы данных. Миграция `20251217_0211_45a7b8c9d1ef_seed_initial_data.py` создает:

1. Администратора с email: `admin@vertex.local` и паролем: `admin123`
2. Компанию по умолчанию с названием `Vertex AR`

Эти данные создаются только если они еще не существуют в базе данных.

## Backup и restore процедуры

### Создание бэкапа

Для создания бэкапа базы данных используйте команду PostgreSQL:

```bash
pg_dump -h localhost -U username -d database_name > backup_file.sql
```

### Восстановление из бэкапа

Для восстановления из бэкапа:

```bash
psql -h localhost -U username -d database_name < backup_file.sql
```

### Автоматические бэкапы

Для автоматизации бэкапов можно использовать cron-задачи или специализированные инструменты, такие как pgBackRest или Barman.

## Оптимизация и индексы

### Основные индексы

1. **Первичные индексы**: автоматически создаются для всех полей с PRIMARY KEY
2. **Уникальные индексы**: на полях с UNIQUE ограничениями
3. **Поисковые индексы**: на часто используемых полях для поиска

### Рекомендуемые индексы

1. **Индексы на внешних ключах**:
   - `projects.company_id`
   - `ar_content.project_id`
   - `ar_content.company_id`
   - `videos.ar_content_id`

2. **Индексы на часто запрашиваемых полях**:
   - `users.email`
   - `companies.name`
   - `projects.name`
   - `ar_content.order_number`
   - `ar_content.unique_id`

3. **Композитные индексы**:
   - `(company_id, project_id)` для таблиц, связанных с проектами
   - `(project_id, order_number)` для ar_content
   - `(created_at, company_id)` для аналитических запросов

### Оптимизация запросов

1. **Использование индексов**: убедитесь, что часто используемые поля проиндексированы
2. **Ограничение результатов**: используйте LIMIT и OFFSET для больших наборов данных
3. **Соединения**: оптимизируйте JOIN-запросы с использованием индексов
4. **Агрегация**: используйте индексы для GROUP BY и ORDER BY операций