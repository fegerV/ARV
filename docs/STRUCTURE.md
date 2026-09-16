# Структура репозитория ARV

Репозиторий организован как **монорепо**: бэкенд и веб-админка в одной кодовой базе, мобильные клиенты — в подкаталогах.

## Верхний уровень

| Каталог | Назначение |
|---------|------------|
| **app/** | Backend: FastAPI-приложение (API, HTML-маршруты, сервисы, модели, конфигурация). |
| **templates/** | HTML-шаблоны (Jinja2) для админки, лендинга и страницы `/view/{unique_id}`. |
| **alembic/** | Миграции БД (PostgreSQL / SQLite). |
| **tests/** | Тесты бэкенда (pytest, pytest-asyncio). |
| **docs/** | Документация: архитектура, API, эксплуатация, аудиты. |
| **deploy/** | Прод-конфигурация: `nginx/`, `systemd/`, `backup/`, `certbot/`. |
| **scripts/** | Скрипты сборки, деплоя и проверок (`run_tests.sh` — точка входа для тестов). |
| **utilities/** | Разовые диагностические скрипты (проверка БД, контейнеров, сидов). |
| **static/** | CSS, JS, изображения для веб-интерфейса. |
| **styles/** | Исходник Tailwind (`input.css`), из которого собирается `static/css`. |
| **prometheus/** | Правила алертов и конфиг скрейпинга метрик. |
| **android/** | V-Portal — Android-приложение (ARCore + Kotlin). |
| **ios/** | ARViewer — iOS-приложение (Swift). |
| **test_data/** | Бинарные фикстуры для тестов (видео, изображение). |
| **test_pages/** | Отладочные HTML-страницы. |
| **data/** | Runtime-данные (очередь алертов). |
| **ssl/** | Заглушка каталога сертификатов (сами ключи не хранятся в репозитории). |

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
| `backups.py` | Бэкапы БД (запуск, история, скачивание, статус) |
| `viewer.py` | API для мобильного AR Viewer |
| `rotation.py` | Ротация видео (расписание) |
| `analytics.py` | Аналитика просмотров |
| `notifications.py` | Система уведомлений |
| `alerts_ws.py` | WebSocket для алертов мониторинга |
| `ai.py` | AI-пайплайн |
| `public.py` | Публичные эндпоинты (лендинг, assetlinks) |
| `settings.py` | API настроек |
| `health.py` | Health-check (`/api/health`) |
| `oauth.py` | OAuth (Yandex) |

### HTML-маршруты (app/html/routes/)

Серверный рендеринг страниц админки:

| Модуль | Страница |
|--------|----------|
| `dashboard.py` | Главная (статистика) |
| `companies.py` | Список / форма компаний |
| `projects.py` | Список / форма проектов |
| `ar_content.py` | Список / детали / форма AR-контента |
| `settings.py` | Настройки (вкладки в `templates/partials/settings_*_tab.html`) |
| `backups.py` | Страница «Бэкапы» |
| `notifications.py` | Уведомления |
| `analytics.py` | Аналитика |
| `storage.py` | Файловое хранилище |
| `auth.py` | Логин |
| `help_routes.py` | Раздел помощи |
| `logs.py`, `debug.py` | Просмотр логов и отладка (для супер-админа) |
| `htmx.py` | htmx-фрагменты |

### Ядро (app/core/)

| Модуль | Назначение |
|--------|-----------|
| `config.py` | Pydantic Settings, переменные окружения |
| `database.py` | AsyncSession, engine, `get_db()`, startup seeding |
| `security.py` | JWT, хеширование паролей |
| `scheduler.py` | APScheduler — расписание бэкапов + межпроцессный `flock` |
| `redis.py` | Подключение к Redis |
| `storage_providers.py` | Фабрика провайдеров хранилища |
| `yandex_disk_provider.py` | Провайдер Яндекс Диска |

### Middleware (app/middleware/)

| Модуль | Назначение |
|--------|-----------|
| `csrf.py` | CSRF-защита state-changing запросов |
| `rate_limiter.py` | Ограничение частоты запросов |
| `maintenance.py` | Режим обслуживания |
| `site_context.py` | Контекст сайта для шаблонов |

### Модели (app/models/)

SQLAlchemy модели: `Company`, `Project`, `ARContent`, `Video`, `VideoRotationSchedule`, `User`, `Notification`, `ARViewSession`, `BackupHistory`, `SystemSettings` и др.

### Сервисы (app/services/)

| Сервис | Назначение |
|--------|-----------|
| `backup_service.py` | pg_dump → gzip → `age` → загрузка на YD → ротация |
| `backup_rotation.py` | Чистые функции выбора по GFS-лестнице (7/4/12/3) |
| `media_backup_service.py` | Restic-снапшоты медиа |
| `restore_service.py` | Восстановление: `verify` / `drill` / `restore`, в т.ч. `--from-file` |
| `backup_metrics.py` | Метрики Prometheus по бэкапам |
| `settings_service.py` | CRUD настроек (все категории) |
| `thumbnail_service.py` | Генерация превью (WebP, 3 размера) |
| `marker_service.py` | AR-маркеры |
| `notification_service.py` | Создание уведомлений |
| `email_transport.py` | Отправка почты |
| `alert_service.py` | Алерты мониторинга |
| `reliability_service.py` | Health-check цикл и надёжность |
| `video_scheduler.py` | Планирование ротации видео |

### CLI (app/cli/)

`backup.py` — команды `status`, `run`, `list`, `download`, `verify`, `drill`, `restore`
(включая `--from-file`, `--encrypted`, `--record-as`). Запуск: `python -m app.cli.backup ...`.

### Фоновые задачи (app/background_tasks/)

`email_tasks.py`, `processing_tasks.py`, `storage_tasks.py`.

## Шаблоны (templates/)

```
templates/
├── base.html                   # Базовый layout (CDN, Alpine, sidebar)
├── base_auth.html              # Layout для страниц входа
├── settings.html               # Настройки (вкладки в partials/)
├── partials/settings_*_tab.html # general, security, storage, notifications, ar, backup
├── analytics.html              # Аналитика
├── notifications.html          # Уведомления
├── storage.html                # Хранилище
├── help.html                   # Помощь
├── index.html / landing.html   # Публичные страницы
├── ar_viewer.html / viewer.html # AR-просмотрщик
├── admin/                      # dashboard, login
├── auth/                       # login
├── companies/                  # list, detail, form
├── projects/                   # list, detail, form
├── ar-content/                 # list, detail, form
├── notifications/              # detail
├── analytics/                  # фрагменты аналитики
├── help/                       # разделы помощи
├── macros/                     # Jinja2-макросы
└── components/                 # sidebar, header, toast, modals, pagination, lightbox
```

## Деплой (deploy/)

| Каталог | Назначение |
|---------|-----------|
| `deploy/backup/` | `backup-db.sh`, `backup-media.sh`, `backup-secrets.sh`, `recover.sh`, `restore.sh`, `common.sh` |
| `deploy/systemd/` | Юниты и таймеры (`arv.service`, `arv-backup-*.timer`) |
| `deploy/nginx/` | Конфиг reverse-proxy |
| `deploy/certbot/` | Настройка перевыпуска сертификатов |

## Мобильные клиенты

- **Android** (`android/`) — V-Portal, ARCore + Kotlin. Подробнее: [android/README.md](../android/README.md).
- **iOS** (`ios/`) — ARViewer, Swift. Релиз: [IOS_RELEASE_GUIDE.md](IOS_RELEASE_GUIDE.md).

## Документация (docs/)

`ARCHITECTURE.md`, `API.md`, `DATA_MODELS.md`, `SERVICES.md`, `DEPLOYMENT.md`,
`STORAGE.md`, `SECURITY.md`, `BACKUP_AND_RECOVERY.md`, `RESTORE_RUNBOOK.md`,
`SECURITY_AUDIT_REPORT.md`, `IDOR_BOLA_AUDIT.md` и др.

Подробнее об архитектуре: [ARCHITECTURE.md](ARCHITECTURE.md).
