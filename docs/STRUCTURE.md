# Структура репозитория ARV

Репозиторий организован как **монорепо**: бэкенд и веб-админка в одной кодовой базе, мобильное приложение AR Viewer — в подкаталоге.

## Основные части

| Каталог | Назначение |
|---------|------------|
| **app/** | Backend: FastAPI-приложение (API, HTML-маршруты, сервисы, модели, конфигурация). |
| **android/** | AR Viewer — Android-приложение (ARCore + Kotlin) для просмотра AR по маркеру. |
| **templates/** | HTML-шаблоны (Jinja2) для админки и лендинга `/view/{unique_id}`. |
| **static/** | CSS, JS, статика для веб-интерфейса. |
| **alembic/** | Миграции БД (PostgreSQL / SQLite). |
| **docs/** | Документация (API, архитектура, troubleshooting и т.д.). |
| **tests/** | Тесты бэкенда (pytest, pytest-asyncio). |
| **scripts/** | Вспомогательные скрипты (проверки, тестовые данные). |

## Backend (app/)

### API (app/api/routes/)

REST API endpoints:

| Модуль | Описание |
|--------|----------|
| `auth.py` | Аутентификация (JWT, login, register) |
| `companies.py` | CRUD компаний |
| `projects.py` | CRUD проектов |
| `ar_content.py` | CRUD AR-контента |
| `videos.py` | Управление видео (загрузка, удаление, превью) |
| `storage.py` | Хранилище файлов, прокси Яндекс Диска |
| `backups.py` | Бэкапы БД (запуск, история, статус) |
| `viewer.py` | API для мобильного AR Viewer |
| `rotation.py` | Ротация видео (расписание) |
| `analytics.py` | Аналитика просмотров |
| `notifications.py` | Система уведомлений |
| `settings.py` | API настроек |
| `health.py` | Health-check |
| `oauth.py` | OAuth (Yandex) |

### HTML-маршруты (app/html/routes/)

Серверный рендеринг страниц админки:

| Модуль | Страница |
|--------|----------|
| `dashboard.py` | Главная (статистика) |
| `companies.py` | Список / форма компаний |
| `projects.py` | Список / форма проектов |
| `ar_content.py` | Список / детали / форма AR-контента |
| `settings.py` | Настройки (вкладки: общие, безопасность, AR, бэкапы) |
| `notifications.py` | Уведомления |
| `analytics.py` | Аналитика |
| `storage.py` | Файловое хранилище |
| `Auth.py` | Логин |

### Ядро (app/core/)

| Модуль | Назначение |
|--------|-----------|
| `config.py` | Pydantic Settings, переменные окружения |
| `database.py` | AsyncSession, engine, `get_db()`, `seed_defaults()` |
| `security.py` | JWT, хеширование паролей |
| `scheduler.py` | APScheduler — расписание бэкапов |
| `storage_providers.py` | Фабрика провайдеров хранилища |
| `yandex_disk_provider.py` | Провайдер Яндекс Диска |

### Модели (app/models/)

SQLAlchemy модели: `Company`, `Project`, `ARContent`, `Video`, `VideoRotationSchedule`, `User`, `Notification`, `ARViewSession`, `BackupHistory`, `SystemSettings` и др.

### Сервисы (app/services/)

| Сервис | Назначение |
|--------|-----------|
| `backup_service.py` | pg_dump → gzip → загрузка на YD → ротация |
| `settings_service.py` | CRUD настроек (все категории) |
| `thumbnail_service.py` | Генерация превью (WebP, 3 размера) |
| `marker_service.py` | AR-маркеры |
| `notification_service.py` | Создание уведомлений |
| `video_scheduler.py` | Планирование ротации видео |

## Шаблоны (templates/)

```
templates/
├── base.html                   # Базовый layout (CDN, Alpine, sidebar)
├── settings.html               # Настройки (4 вкладки)
├── analytics.html              # Аналитика
├── notifications.html          # Уведомления
├── storage.html                # Хранилище
├── admin/
│   ├── dashboard.html          # Главная
│   └── login.html              # Авторизация (устар.)
├── auth/login.html             # Авторизация
├── companies/                  # list, detail, form
├── projects/                   # list, detail, form
├── ar-content/                 # list, detail, form
├── notifications/detail.html
└── components/                 # sidebar, header, toast, lightbox, pagination
```

## AR Viewer (android/)

Android-приложение (ARCore + Kotlin). Подробнее: [android/README.md](../android/README.md).

Подробнее об архитектуре: [ARCHITECTURE.md](ARCHITECTURE.md).
