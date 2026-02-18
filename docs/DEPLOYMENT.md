# Развёртывание Vertex AR

## Требования

- Python 3.11+
- PostgreSQL 12+ (продакшен)
- Docker & Docker Compose (опционально)
- Nginx (reverse proxy, продакшен)
- Git
- ffmpeg (для генерации превью видео)

## Локальное развертывание (разработка)

### 1. Клонирование и настройка

```bash
git clone https://github.com/fegerV/ARV
cd ARV
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 2. Переменные окружения

```bash
cp .env.example .env
```

Ключевые переменные для разработки:

```bash
DATABASE_URL=sqlite+aiosqlite:///./test_vertex_ar.db
SECRET_KEY=dev-secret-key
STORAGE_BASE_PATH=./storage
LOCAL_STORAGE_PATH=./storage
LOG_LEVEL=DEBUG
```

### 3. Миграции и запуск

```bash
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Проверка

- Админ-панель: http://localhost:8000/admin
- API документация: http://localhost:8000/docs
- Health check: http://localhost:8000/health
- Логин: `admin@vertexar.com` / `admin123`

## Продуктивное развёртывание (Ubuntu + systemd)

Это текущая конфигурация боевого сервера `ar.neuroimagen.ru`.

### 1. Подготовка сервера

```bash
sudo useradd -r -s /bin/bash -d /opt/arv arv
sudo mkdir -p /opt/arv/{app,storage,venv}
sudo chown -R arv:arv /opt/arv
```

### 2. Клонирование и установка

```bash
sudo -u arv bash -c 'cd /opt/arv && git clone https://github.com/fegerV/ARV app'
sudo -u arv bash -c 'cd /opt/arv && python3 -m venv venv'
sudo -u arv bash -c 'cd /opt/arv/app && source /opt/arv/venv/bin/activate && pip install -r requirements.txt'
```

### 3. Переменные окружения

```bash
# /opt/arv/app/.env
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql+asyncpg://arv:PASSWORD@localhost:5432/arv
SECRET_KEY=your-production-secret
STORAGE_BASE_PATH=/opt/arv/storage
LOCAL_STORAGE_PATH=/opt/arv/storage
PUBLIC_URL=https://ar.neuroimagen.ru
LOG_LEVEL=INFO
```

### 4. Миграции

```bash
sudo -u arv bash -c 'cd /opt/arv/app && source /opt/arv/venv/bin/activate && alembic upgrade head'
```

### 5. Systemd-юнит

```ini
# /etc/systemd/system/arv.service
[Unit]
Description=Vertex AR FastAPI Application
After=network.target postgresql.service

[Service]
Type=simple
User=arv
WorkingDirectory=/opt/arv/app
ExecStart=/opt/arv/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2 --log-level info --access-log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable arv
sudo systemctl start arv
```

### 6. Nginx (reverse proxy)

```nginx
server {
    listen 443 ssl http2;
    server_name ar.neuroimagen.ru;

    ssl_certificate     /etc/letsencrypt/live/ar.neuroimagen.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ar.neuroimagen.ru/privkey.pem;

    client_max_body_size 200M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /storage/ {
        alias /opt/arv/storage/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

## Обновление на сервере

```bash
sudo -u arv bash -c 'cd /opt/arv/app && git pull'
sudo -u arv bash -c 'cd /opt/arv/app && source /opt/arv/venv/bin/activate && pip install -r requirements.txt'
sudo -u arv bash -c 'cd /opt/arv/app && source /opt/arv/venv/bin/activate && alembic upgrade head'
# Сборка CSS (Tailwind) — если менялись шаблоны или styles/
sudo -u arv bash -c 'cd /opt/arv/app && npm ci && npm run build:css'
sudo systemctl restart arv
```

## Docker Compose (альтернативный вариант)

```bash
cp .env.example .env.production
# Настройте переменные окружения
docker compose up -d --build
```

## Мониторинг и логи

```bash
# Статус сервиса
sudo systemctl status arv

# Логи приложения (последние 100 строк)
sudo journalctl -u arv -n 100 --no-pager

# Логи в реальном времени
sudo journalctl -u arv -f

# Логи Nginx
sudo journalctl -u nginx -n 50

# Docker логи (при использовании Docker Compose)
docker compose logs -f app
```

## Бэкапы БД

Бэкапы настраиваются через админку: **Settings → Бэкапы**. Подробности:

- Автоматический бэкап PostgreSQL → gzip → Яндекс Диск
- Расписание: ежедневно, каждые 12ч, еженедельно, custom cron
- Ротация по возрасту (дни) и количеству копий
- Ручной запуск через кнопку в UI
- API: `POST /api/backups/run`

## Troubleshooting

### Сервис не запускается

```bash
sudo journalctl -u arv -n 50 --no-pager
# Проверьте ошибки в выводе
```

### Проблемы с миграциями

```bash
sudo -u arv bash -c 'cd /opt/arv/app && source /opt/arv/venv/bin/activate && alembic current'
sudo -u arv bash -c 'cd /opt/arv/app && source /opt/arv/venv/bin/activate && alembic upgrade head'
```

### Видео не загружается / нет превью

- Проверьте наличие `ffmpeg`: `which ffmpeg`
- Проверьте права на `STORAGE_BASE_PATH`
- Логи: `sudo journalctl -u arv --grep "thumbnail\|ffmpeg\|video" -n 50`

### Яндекс Диск ошибки

- Проверьте срок действия OAuth-токена компании
- Логи: `sudo journalctl -u arv --grep "yd_\|yandex\|DiskPath" -n 50`
