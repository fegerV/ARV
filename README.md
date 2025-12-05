# Vertex AR B2B Platform

B2B SaaS платформа для создания AR-контента на основе распознавания изображений (NFT markers).

## 🚀 Быстрый старт

### Требования
- Docker Desktop (Windows) или Docker + Docker Compose (Linux)
- WSL2 для Windows (рекомендуется)
- Python 3.11+ (для локальной разработки)
- Node.js 18+ (для frontend разработки)

### Установка и запуск

```bash
# 1. Клонировать репозиторий
git clone <repository-url>
cd vertex-ar

# 2. Создать .env файл
cp .env.example .env

# 3. Запустить все сервисы
docker compose up -d

# 4. Применить миграции
docker compose exec app alembic upgrade head

# 5. Создать первого администратора
docker compose exec app python scripts/create_first_admin.py

# 6. Открыть приложение
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Admin Panel: http://localhost:3000
```

## 📁 Структура проекта

```
vertex-ar/
├── app/                    # Backend FastAPI приложение
│   ├── core/              # Конфигурация, БД, безопасность
│   ├── models/            # SQLAlchemy модели
│   ├── schemas/           # Pydantic схемы
│   ├── api/               # API endpoints
│   ├── services/          # Бизнес-логика
│   ├── tasks/             # Celery задачи
│   └── utils/             # Вспомогательные функции
├── frontend/              # React Admin Panel
├── alembic/               # Миграции базы данных
├── storage/               # Локальное хранилище (только dev)
├── tests/                 # Тесты
├── scripts/               # Служебные скрипты
├── docker-compose.yml     # Производственная конфигурация
├── docker-compose.override.yml  # Development настройки
└── docs/                  # Документация
```

## 🛠 Технологии

- **Backend**: FastAPI 0.109, SQLAlchemy 2.0 async, PostgreSQL 15
- **Frontend**: React 18, TypeScript, Material-UI 5, TailwindCSS
- **Queue**: Celery 5.3, Redis 7
- **AR Engine**: Mind AR 1.2.5, Three.js 0.158
- **Storage**: Local/MinIO/Yandex Disk
- **Monitoring**: Prometheus, Grafana, Sentry

## 📚 Документация

- [Архитектура системы](docs/01-architecture.md)
- [API Reference](docs/02-api-reference.md)
- [Deployment](docs/03-deployment.md)
- [Monitoring](docs/04-monitoring.md)
- [Backup & Recovery](docs/05-backup-recovery.md)
- [Developer Onboarding](docs/06-onboarding.md)

## 🔧 Разработка

### Backend разработка

```bash
# Установить зависимости
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Запустить в dev режиме
uvicorn app.main:app --reload --port 8000
```

### Frontend разработка

```bash
cd frontend
npm install
npm run dev
```

### Запуск тестов

```bash
# Backend тесты
pytest tests/ -v --cov=app

# Frontend тесты
cd frontend
npm run test
```

## 🌍 Environment Variables

Основные переменные окружения (полный список в `.env.example`):

```env
# Database
DATABASE_URL=postgresql+asyncpg://vertex_ar:password@postgres:5432/vertex_ar

# Redis
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=your-super-secret-key-change-in-production

# Storage
STORAGE_TYPE=local  # local, minio, yandex_disk

# Notifications
SMTP_HOST=smtp.gmail.com
TELEGRAM_BOT_TOKEN=your-bot-token
```

## 🎯 Phase 1 (Current) - Core Infrastructure

- [x] Docker Compose configuration
- [x] FastAPI skeleton
- [x] PostgreSQL + Alembic migrations
- [x] Local storage
- [x] Health check endpoints
- [x] Structured logging

## 📝 License

Proprietary - All rights reserved

## 👥 Team

Vertex AR Development Team
