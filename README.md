# ARV — Платформа для создания AR-контента

B2B SaaS платформа для создания AR-контента на основе распознавания изображений (NFT markers).

## Архитектура

- **Backend**: FastAPI — API + серверный HTML-рендеринг (Jinja2)
- **Frontend**: htmx + Alpine.js + Tailwind CSS (CDN, без сборки)
- **БД**: PostgreSQL (продакшен) / SQLite (локальная разработка)
- **Хранилище**: локальное или Яндекс Диск (выбирается на уровне компании)
- **Бэкапы**: автоматическое резервное копирование PostgreSQL на Яндекс Диск (APScheduler)
- **AR**: Android-приложение «V-Portal» (ARCore + Kotlin)

## Технологический стек

| Категория | Технологии |
|-----------|-----------|
| Backend | Python 3.11+, FastAPI 0.109, SQLAlchemy 2.0 (async), Alembic, Pydantic 2 |
| Frontend | Jinja2, htmx, Alpine.js, Tailwind CSS, Material Icons |
| БД | PostgreSQL 16 + asyncpg, SQLite (dev) |
| Хранилище | Локальное FS, Яндекс Диск API |
| Планировщик | APScheduler (AsyncIOScheduler) |
| Сервер | Uvicorn (ASGI), Nginx (reverse proxy в production) |
| Мониторинг | structlog, Prometheus client |
| Тесты | pytest, pytest-asyncio, httpx |

## Быстрый старт

### 1. Клонирование и настройка

```bash
git clone https://github.com/fegerV/ARV
cd ARV
cp .env.example .env
# Отредактируйте .env
```

### 2. Запуск

**Docker Compose (рекомендуется):**
```bash
docker compose up -d
```

**Локально:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Вход в админку

- URL: http://localhost:8000/admin
- Email: `admin@vertexar.com`
- Пароль: `admin123`

> **Сразу после первого входа смените пароль!**

## Структура проекта

```
ARV/
├── app/                        # Backend (FastAPI)
│   ├── api/routes/             # REST API endpoints
│   ├── html/routes/            # Серверные HTML-страницы
│   ├── core/                   # Config, DB, security, scheduler
│   ├── models/                 # SQLAlchemy модели
│   ├── schemas/                # Pydantic схемы
│   ├── services/               # Бизнес-логика
│   ├── middleware/             # CSRF, rate limiting
│   ├── background_tasks/       # Фоновые задачи
│   ├── cli/                    # CLI: бэкап, восстановление, проверки
│   └── utils/                  # Утилиты
├── templates/                  # Jinja2 шаблоны (+ partials/)
├── alembic/                    # Миграции БД
├── tests/                      # Тесты
├── docs/                       # Документация (в т.ч. RESTORE_RUNBOOK.md)
├── deploy/                     # Прод: nginx, systemd, backup, certbot
├── scripts/                    # Скрипты сборки/деплоя/проверок
├── utilities/                  # Разовые диагностические скрипты
├── android/                    # V-Portal (Android, ARCore + Kotlin)
├── ios/                        # ARViewer (iOS, Swift)
├── prometheus/                 # Метрики и правила алертов
├── static/                     # Статика (css, js, img)
├── styles/                     # Исходник Tailwind
├── test_data/                  # Фикстуры для тестов
├── test_pages/                 # Отладочные HTML-страницы
├── data/                       # Runtime-данные
├── requirements.txt            # Python-зависимости
├── docker-compose.yml          # Docker Compose
└── .env.example                # Шаблон переменных окружения
```

## Ключевые возможности

### Админ-панель
- Управление компаниями, проектами, AR-контентом
- Загрузка фото/видео — локально или на Яндекс Диск
- Генерация QR-кодов и превью (WebP, 3 размера)
- Режимы воспроизведения: ручной, последовательный, циклический
- Система уведомлений
- Аналитика просмотров (по дням, устройствам, браузерам)

### Бэкапы БД
- Автоматическое резервное копирование PostgreSQL на Яндекс Диск
- Настройка через админку: Settings → Бэкапы
- Расписание: ежедневно, каждые 12ч, еженедельно, custom cron
- Ротация: GFS-лестница (7 ежедневных / 4 недельных / 12 месячных / 3 годовых), настраивается в админке
- Шифрование дампов (`age`), проверка целостности (`verify`) и пробное восстановление (`drill`)
- Ручной запуск и скачивание артефакта из UI
- История операций с отображением статуса и размера
- Восстановление одной командой, в том числе без живой БД — см. [RESTORE_RUNBOOK.md](docs/RESTORE_RUNBOOK.md)

### Хранилище
- Два провайдера: локальное FS и Яндекс Диск
- Выбор провайдера на уровне компании
- Прокси для файлов с Яндекс Диска (поддержка HTTP Range)
- Автогенерация thumbnails (WebP, 3 размера: 150×112, 320×240, 640×480)

### Безопасность
- JWT-аутентификация (cookie + Bearer)
- Rate limiting (5 попыток / 15 минут)
- CORS, валидация через Pydantic
- Защита API-эндпоинтов аутентификацией

### V-Portal (Android)
- Просмотр AR через приложение (ARCore)
- Deep links: `arv://view/{unique_id}` + App Links
- API манифест: `GET /api/viewer/ar/{unique_id}/manifest`
- Верификация: `/.well-known/assetlinks.json`

## Команды разработки

```bash
# Запуск сервера
uvicorn app.main:app --reload --port 8000

# Тесты — ВСЕГДА через скрипт: он подгружает .env.test и сам выбирает venv.
# Голый `pytest` унаследует боевой .env и упадёт на валидации Settings.
bash scripts/run_tests.sh -q
bash scripts/run_tests.sh tests/test_backup_cli.py -q --no-cov

# Миграции
alembic upgrade head
alembic revision --autogenerate -m "описание"
```

> Тесты, требующие OpenCV, требуют установленного `opencv-python`; без него
> исключайте `tests/test_marker_service.py` (`--ignore=`).

## Развёртывание на сервере

```bash
# На сервере (Ubuntu)
sudo -u arv bash -c 'cd /opt/arv/app && git pull'
sudo -u arv bash -c 'cd /opt/arv/app && source /opt/arv/venv/bin/activate && pip install -r requirements.txt'
sudo -u arv bash -c 'cd /opt/arv/app && source /opt/arv/venv/bin/activate && alembic upgrade head'
sudo systemctl restart arv
```

Подробнее: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

## Документация

| Документ | Описание |
|----------|----------|
| **Архитектура и разработка** | |
| [Architecture](docs/ARCHITECTURE.md) | Архитектура системы |
| [Tech Stack](docs/TECH_STACK.md) | Технологический стек и обоснование |
| [Structure](docs/STRUCTURE.md) | Структура репозитория |
| [Data Models](docs/DATA_MODELS.md) | Модели данных и схема БД |
| [Services](docs/SERVICES.md) | Описание сервисов |
| [Migrations](docs/MIGRATIONS.md) | Миграции БД |
| [Performance](docs/PERFORMANCE.md) | Производительность |
| **API и аутентификация** | |
| [API Reference](docs/API.md) | Полная документация API |
| [API Examples](docs/API_EXAMPLES.md) | Примеры запросов |
| [Auth System](docs/AUTH_SYSTEM.md) | Система аутентификации |
| **Эксплуатация** | |
| [Deployment](docs/DEPLOYMENT.md) | Руководство по развёртыванию |
| [Storage](docs/STORAGE.md) | Система хранения файлов |
| [Backup & DR](docs/BACKUP_AND_RECOVERY.md) | Резервное копирование, ротация, концепция восстановления |
| [Restore Runbook](docs/RESTORE_RUNBOOK.md) | **Оперативное восстановление из бэкапа** (пошагово) |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Решение проблем |
| [Manual Testing Guide](docs/MANUAL_TESTING_GUIDE.md) | Ручное тестирование |
| **Безопасность** | |
| [Security](docs/SECURITY.md) | Политика безопасности |
| [Security Audit Report](docs/SECURITY_AUDIT_REPORT.md) | Отчёт аудита и статус устранения находок |
| [IDOR/BOLA Audit](docs/IDOR_BOLA_AUDIT.md) | Аудит защиты от IDOR/BOLA уязвимостей |
| **Мобильные клиенты** | |
| [Android App](docs/ANDROID_APP.md) | V-Portal: описание и сборка |
| [Android Studio Setup](docs/ANDROID_STUDIO_SETUP.md) | Настройка окружения Android |
| [ARCore Floating Playback Plan](docs/ARCORE_FLOATING_PLAYBACK_PLAN.md) | План доработки AR-плеера |
| [AR Viewer Troubleshooting](docs/AR_VIEWER_TROUBLESHOOTING.md) | Проблемы AR-просмотрщика |
| [iOS Release Guide](docs/IOS_RELEASE_GUIDE.md) | Релиз ARViewer в App Store |

Интерактивная документация API: http://localhost:8000/docs

## Статус

- **Версия**: 2.2.0
- **Лицензия**: Proprietary

### Безопасность

- JWT-аутентификация (cookie + Bearer)
- Rate limiting (5 попыток / 15 минут)
- CORS, валидация через Pydantic
- CSRF-защита на всех state-changing запросах
- Company-based ownership checks на всех защищенных endpoints (IDOR/BOLA защита)
- Super-admin режим для полного доступа
