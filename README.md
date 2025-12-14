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

# 4. Применить миграции (создает администратора и компанию по умолчанию)
docker compose exec app alembic upgrade head

# 5. Открыть приложение
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Admin Panel: http://localhost:3000
```

### 🔑 Данные для входа по умолчанию

После первого запуска автоматически создается администратор:

- **Email**: `admin@vertexar.com`
- **Пароль**: `admin123`

⚠️ **ВАЖНО**: Немедленно измените пароль администратора после первого входа!

### ⚙️ Настройка администратора

Вы можете настроить учетные данные администратора через переменные окружения в `.env`:

```env
# Настройки администратора
ADMIN_EMAIL=your-admin@company.com
ADMIN_DEFAULT_PASSWORD=YourSecurePassword123!
```

**Примечание**: В текущей версии администратор создается через миграции с жестко заданными учетными данными. Поддержка переменных окружения запланирована в следующих версиях.

## 📁 Структура проекта

```
vertex-ar/
├── app/                    # Backend FastAPI приложение
│   ├── core/              # Конфигурация, БД, безопасность
│   ├── models/            # SQLAlchemy модели
│   ├── schemas/           # Pydantic схемы
│   ├── api/               # API endpoints
│   ├── services/          # Бизнес-логика
│   └── utils/             # Вспомогательные функции
├── frontend/              # React Admin Panel
├── alembic/               # Миграции базы данных
├── storage/               # Локальное хранилище (только dev)
├── tests/                 # Тесты
├── scripts/               # Служебные скрипты
├── docker-compose.yml     # Производственная конфигурация
├── docker-compose.override.yml  # Development настройки
```

## 🛠 Технологии

- **Backend**: FastAPI 0.109, SQLAlchemy 2.0 async, PostgreSQL 15
- **Frontend**: React 18, TypeScript, Material-UI 5, TailwindCSS
- **Background Tasks**: FastAPI BackgroundTasks
- **AR Engine**: Mind AR 1.2.5, Three.js 0.158
- **Storage**: Local/MinIO/Yandex Disk
- **Monitoring**: Prometheus, Grafana, Sentry

## 📚 Документация

Проект упрощён до монолита (FastAPI + локальное хранилище + React Admin). Исторические файлы-отчёты по миграциям/рефакторингу сохранены в корне репозитория и в `frontend/`, но **источником правды** считается этот `README.md`.

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

Основные переменные окружения (см. `.env.example`):

```env
# Database
DATABASE_URL=postgresql+asyncpg://vertex_ar:password@postgres:5432/vertex_ar

# Public URL (для QR-кодов)
PUBLIC_URL=http://localhost:8000

# Media root (локальное хранилище)
MEDIA_ROOT=/app/storage/content

# Logging
LOG_LEVEL=INFO
```

## 🎯 Phase 1 (Current) - Core Infrastructure

- [x] Docker Compose configuration
- [x] FastAPI skeleton
- [x] PostgreSQL + Alembic migrations
- [x] Local storage
- [x] Health check endpoints
- [x] Structured logging

## 🌐 Docker Networking Diagnostics

The platform includes comprehensive Docker networking diagnostics to help troubleshoot connectivity issues between services.

### Diagnostic Script

A POSIX-compliant diagnostic script is available at `scripts/diagnose_docker_network.sh` that provides:

- Docker daemon and network status checking
- Container IP address listing
- DNS resolution tests between services
- Cross-container connectivity tests
- Service health status monitoring
- Troubleshooting tips and quick reference commands

### Running the Diagnostic Script

```bash
# Make the script executable (Linux/Mac)
chmod +x scripts/diagnose_docker_network.sh

# Run the diagnostic
./scripts/diagnose_docker_network.sh
```

### Network Architecture

All services communicate via Docker DNS on the shared `vertex_net` network:

- Single named bridge network: `vertex_net` (subnet 172.20.0.0/16)
- All services attached: postgres, redis, app, postgres-exporter, prometheus, grafana
- Service discovery via Docker DNS instead of hard-coded IPs

### Startup Dependency Chain

Services start in the following order with health checks ensuring reliability:

```
postgres → redis → app
postgres-exporter depends on postgres (healthy)
prometheus depends on app (healthy) and postgres-exporter (started)
grafana depends on prometheus (started)
```

### Common Issues and Solutions

1. **Containers can't resolve each other by service name**:
   - Ensure all services are attached to the same network
   - Restart services: `docker compose down && docker compose up -d`

2. **Health checks failing**:
   - Check service logs: `docker compose logs <service>`
   - Verify service configuration and dependencies

3. **Services not starting in correct order**:
   - Check `depends_on` conditions in docker-compose.yml
   - Ensure health checks are properly configured

## 📝 License

Proprietary - All rights reserved

## 🚀 First Launch Checklist

### ✅ Проверка после первого запуска

1. **Проверка входа администратора**:
   ```bash
   # Проверьте, что можете войти с учетными данными по умолчанию
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin@vertexar.com&password=admin123"
   ```

2. **Проверка существования компании по умолчанию**:
   ```bash
   # Проверьте, что компания Vertex AR создана
   curl -X GET http://localhost:8000/api/companies/ \
     -H "Authorization: Bearer <your-jwt-token>"
   ```

3. **Запуск тестов авторизации**:
   ```bash
   # Запустите интеграционные тесты авторизации
   docker compose exec app pytest tests/integration/test_auth_flow.py -v
   ```

4. **Изменение пароля для production**:
   - Войдите в админ-панель: http://localhost:3000
   - Сразу измените пароль администратора
   - Для production: сгенерируйте новый хеш пароля:
     ```bash
     docker compose exec app python -c "
     from app.core.security import get_password_hash
     print(get_password_hash('YourSecurePassword123!'))
     "
     ```
   - Обновите пароль в базе данных:
     ```sql
     UPDATE users SET hashed_password = 'your-new-hash' WHERE email = 'admin@vertexar.com';
     ```

### 🔧 Production настройка

- [ ] Измените пароль администратора
- [ ] Установите сильный `SECRET_KEY` (32+ символов)
- [ ] Настройте HTTPS
- [ ] Проверьте CORS настройки
- [ ] Настройте мониторинг логов авторизации

## 👥 Team

Vertex AR Development Team
