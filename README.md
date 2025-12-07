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
git clone https://github.com/fegerV/ARV.git
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
- **Notifications**: Email (SMTP), Telegram

## 📚 Документация

### Основная документация
- [Архитектура системы](docs/01-architecture.md)
- [Миграции БД](docs/02-migrations.md)
- [Deployment](docs/03-deployment.md)
- [Monitoring](docs/04-monitoring.md)
- [Backup & Recovery](docs/05-backup-recovery.md)

### Storage и Провайдеры
- [🗄️ Storage Providers Guide](docs/STORAGE_PROVIDERS.md) - Конфигурация и использование хранилищ
- [✅ Verification Plan](docs/VERIFICATION_PLAN.md) - План тестирования и валидации
- [Storage Connections Feature](STORAGE_CONNECTIONS_FEATURE.md) - Управление подключениями

### Интеграции и настройки
- [Email Notifications Setup](EMAIL_SETUP.md)
- [Email Notifications Summary](EMAIL_NOTIFICATIONS_SUMMARY.md)
- [Dependency Audit Summary](DEPENDENCY_AUDIT_SUMMARY.md)

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

### 🔍 Запуск верификации Storage

Для комплексной проверки всех storage провайдеров и тестирования:

```bash
# Запустить полный набор верификационных тестов
./scripts/run_verification.sh

# Скрипт последовательно выполнит:
# 1. Unit тесты для storage провайдеров
# 2. Интеграционные тесты API
# 3. E2E тесты административной панели
# 4. Проверку Celery задач
# 5. Ручную проверку storage провайдеров
# 6. Health checks API
# 7. Performance бенчмарки
```

Подробнее о тестировании и верификации см. в [Verification Plan](docs/VERIFICATION_PLAN.md).

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
STORAGE_BASE_PATH=/app/storage/content

# MinIO Configuration (if using MinIO)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=your-minio-access-key
MINIO_SECRET_KEY=your-minio-secret-key
MINIO_BUCKET_NAME=vertex-ar
MINIO_REGION=us-east-1
MINIO_SECURE=false

# Yandex Disk Configuration (if using Yandex Disk)
YANDEX_DISK_OAUTH_TOKEN=your-yandex-oauth-token
YANDEX_DISK_BASE_PATH=/VertexAR

# Email Notifications
MAIL_USERNAME=your_smtp_username
MAIL_PASSWORD=your_smtp_password
MAIL_FROM=noreply@yourdomain.com
MAIL_FROM_NAME="Vertex AR Platform"
MAIL_SERVER=smtp.yandex.ru
MAIL_PORT=465
MAIL_TLS=False
MAIL_SSL=True

# Telegram Notifications
TELEGRAM_BOT_TOKEN=your-bot-token
```

## 🎯 Phase 1 (Current) - Core Infrastructure

- [x] Docker Compose configuration
- [x] FastAPI skeleton
- [x] PostgreSQL + Alembic migrations
- [x] Local storage
- [x] Health check endpoints
- [x] Structured logging
- [x] Email notification system

## 📝 License

Proprietary - All rights reserved

## 👥 Team

Vertex AR Development Team