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

### 6. Nginx (reverse proxy)

Авторитетная конфигурация — `deploy/nginx/arv.conf`. Скрипт деплоя копирует её автоматически в `/etc/nginx/sites-available/arv.conf`.

Краткий актуальный конфиг, который деплой размещает на сервере:

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

upstream arv_backend {
    server 127.0.0.1:8000;
    keepalive 16;
}

server {
    listen 80;
    listen [::]:80;
    server_name ar.neuroimagen.ru;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ar.neuroimagen.ru;

    ssl_certificate     /etc/letsencrypt/live/ar.neuroimagen.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ar.neuroimagen.ru/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header X-XSS-Protection "1; mode=block" always;

    client_max_body_size 120M;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript image/svg+xml;
    gzip_min_length 1000;

    location /static/ {
        alias /opt/arv/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /storage/ {
        alias /opt/arv/storage/;
        expires 7d;
        add_header Cache-Control "public, max-age=604800";
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, OPTIONS" always;
        add_header X-Content-Type-Options nosniff always;
        sendfile on;
        tcp_nopush on;
        tcp_nodelay on;
        try_files $uri =404;
    }

    location = /favicon.ico {
        proxy_pass http://arv_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        add_header Cache-Control "public, max-age=2592000";
    }

    location ~ ^/api/companies/\d+/projects/\d+/ar-content$ {
        limit_req zone=api burst=5 nodelay;
        proxy_pass http://arv_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_connect_timeout 60s;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }

    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://arv_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }

    location / {
        proxy_pass http://arv_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_connect_timeout 30s;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }
}
```

### 7. SSL / Certbot

Боевой Nginx должен ссылаться напрямую на live-ссылки certbot, а не на копии сертификатов:

```nginx
ssl_certificate     /etc/letsencrypt/live/ar.neuroimagen.ru/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/ar.neuroimagen.ru/privkey.pem;
```

Установить renewal hook и ежедневную проверку фактически отдаваемого Nginx сертификата:

```bash
sudo install -D -m 755 deploy/certbot/reload-nginx /etc/letsencrypt/renewal-hooks/deploy/reload-nginx
sudo install -D -m 755 deploy/certbot/check-ar-cert-renewal /usr/local/sbin/check-ar-cert-renewal
sudo install -D -m 644 deploy/certbot/ar-cert-check.cron /etc/cron.d/ar-cert-check

sudo /etc/letsencrypt/renewal-hooks/deploy/reload-nginx
sudo /usr/local/sbin/check-ar-cert-renewal
```

```bash
# Проверить срок действия сертификата
sudo certbot certificates

# Принудительное обновление (dry-run)
sudo certbot renew --dry-run

# Фактическое обновление
sudo certbot renew

# Проверить таймер auto-renewal
systemctl status certbot.timer

# Проверить логи renewal
sudo journalctl -u certbot -n 100

# После renewal Nginx перезагружается автоматически через hook:
# /etc/letsencrypt/renewal-hooks/deploy/reload-nginx
```

Если certbot не настроен на первый выпуск:

```bash
# Вариант A: certbot --nginx (автоматически настроит Nginx)
sudo certbot --nginx -d ar.neuroimagen.ru

# Вариант B: webroot (если Nginx уже слушает 80)
sudo certbot certonly \
    --webroot --webroot-path /var/www/certbot \
    -d ar.neuroimagen.ru \
    --email admin@neuroimagen.ru \
    --agree-tos --non-interactive
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

### Проблемы с SSL / Certbot
- Проверьте срок: `sudo certbot certificates`
- Проверьте auto-renewal: `systemctl list-timers | grep certbot`
- Проверьте сертификат, который реально отдаёт Nginx: `sudo /usr/local/sbin/check-ar-cert-renewal`
- Ручной запуск: `sudo certbot renew --dry-run`, затем `sudo systemctl reload nginx`

### Яндекс Диск ошибки
- Проверьте срок действия OAuth-токена компании
- Логи: `sudo journalctl -u arv --grep "yd_\|yandex\|DiskPath" -n 50`
