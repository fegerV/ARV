# ARV — Платформа для создания AR-контента

B2B SaaS платформа для создания AR-контента на основе распознавания изображений (NFT markers).

## Архитектура

- **Backend**: FastAPI — API + серверный HTML-рендеринг (Jinja2)
- **Frontend**: htmx + Alpine.js + Tailwind CSS (CDN, без сборки)
- **БД**: PostgreSQL (продакшен) / SQLite (локальная разработка)
- **Хранилище**: локальное или Яндекс Диск (выбирается на уровне компании)
- **Бэкапы**: автоматическое резервное копирование PostgreSQL на Яндекс Диск (APScheduler)
- **AR**: Android-приложение «AR Viewer» (ARCore + Kotlin)

## Технологический стек

| Категория | Технологии |
|-----------|-----------|
| Backend | Python 3.11+, FastAPI 0.109, SQLAlchemy 2.0 (async), Alembic, Pydantic 2 |
| Frontend | Jinja2, htmx, Alpine.js, Tailwind CSS, Material Icons |
| БД | PostgreSQL 15 + asyncpg, SQLite (dev) |
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
├── app/                        # Backend
│   ├── api/routes/             # REST API endpoints
│   ├── html/routes/            # Серверные HTML-страницы
│   ├── core/                   # Config, DB, security, scheduler
│   ├── models/                 # SQLAlchemy модели
│   ├── schemas/                # Pydantic схемы
│   ├── services/               # Бизнес-логика
│   └── utils/                  # Утилиты
├── templates/                  # Jinja2 шаблоны
│   ├── components/             # Переиспользуемые компоненты
│   ├── auth/                   # Аутентификация
│   ├── companies/              # Компании
│   ├── projects/               # Проекты
│   ├── ar-content/             # AR-контент
│   ├── notifications/          # Уведомления
│   └── settings.html           # Настройки (вкладки: общие, безопасность, AR, бэкапы)
├── alembic/                    # Миграции БД
├── tests/                      # Тесты
├── docs/                       # Документация
├── scripts/                    # Вспомогательные скрипты
├── android/                    # AR Viewer (Android, ARCore + Kotlin)
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
- Ротация: по возрасту (дни) и количеству копий
- Ручной запуск бэкапа из UI
- История операций с отображением статуса и размера

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

### AR Viewer (Android)
- Просмотр AR через приложение (ARCore)
- Deep links: `arv://view/{unique_id}` + App Links
- API манифест: `GET /api/viewer/ar/{unique_id}/manifest`
- Верификация: `/.well-known/assetlinks.json`

## Команды разработки

```bash
# Запуск сервера
uvicorn app.main:app --reload --port 8000

# Тесты
pytest tests/ -v --cov=app

# Миграции
alembic upgrade head
alembic revision --autogenerate -m "описание"
```

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
| [API Reference](docs/API.md) | Полная документация API |
| [Architecture](docs/ARCHITECTURE.md) | Архитектура системы |
| [Data Models](docs/DATA_MODELS.md) | Модели данных и схема БД |
| [Deployment](docs/DEPLOYMENT.md) | Руководство по развёртыванию |
| [Services](docs/SERVICES.md) | Описание сервисов |
| [Storage](docs/STORAGE.md) | Система хранения файлов |
| [Security](docs/SECURITY.md) | Политика безопасности |
| [Auth System](docs/AUTH_SYSTEM.md) | Система аутентификации |
| [Migrations](docs/MIGRATIONS.md) | Миграции БД |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Решение проблем |

Интерактивная документация API: http://localhost:8000/docs

## Статус

- **Версия**: 2.1.0
- **Лицензия**: Proprietary
