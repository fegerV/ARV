# Деплой приложения ARVlite

## Требования к инфраструктуре

### Сервер
- **VPS/Облако**: рекомендуется Ubuntu 22.04 LTS или новее
- **CPU**: минимум 2 ядра (рекомендуется 4+)
- **RAM**: минимум 4GB (рекомендуется 8GB+)
- **Диск**: минимум 20GB свободного места (рекомендуется 50GB+ для логов и бэкапов)

### Домен и SSL
- Доменное имя, направленное на IP сервера
- SSL сертификат (рекомендуется Let's Encrypt)
- Настройка DNS: A-запись на IP сервера

### Почтовый сервис
- SMTP конфигурация для отправки уведомлений
- Поддерживаемые провайдеры: SendGrid, Mailgun, Gmail, собственный SMTP

## Виды деплоя

### 1. Docker Compose (рекомендуемый)

#### Подготовка сервера
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### Клонирование репозитория
```bash
git clone https://github.com/your-repo/ARVlite.git
cd ARVlite/ARV
```

#### Конфигурация .env для продакшена
Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
nano .env
```

Пример продакшен конфигурации:
```
# Database
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=arvlite_prod
POSTGRES_USER=arvlite_user
POSTGRES_PASSWORD=your_secure_password

# Security
SECRET_KEY=your_production_secret_key
JWT_SECRET_KEY=your_jwt_secret
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Email
SMTP_HOST=smtp.yourmailprovider.com
SMTP_PORT=587
SMTP_USER=your_smtp_user
SMTP_PASSWORD=your_smtp_password

# Frontend
FRONTEND_URL=https://yourdomain.com

# Storage
STORAGE_PATH=/var/lib/arvlite/storage
```

#### Запуск приложения
```bash
# Запуск в фоне
docker-compose up -d

# Проверка статуса контейнеров
docker-compose ps
```

#### PostgreSQL persistence
Данные PostgreSQL сохраняются в Docker volume:
```yaml
# docker-compose.yml
volumes:
  postgres_data:
    driver: local
```

#### Автоматический backup
Конфигурация ротации и бэкапов в `docker-compose.yml`:
```yaml
services:
  db:
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backup:/backup
```

### 2. Systemd (без Docker)

#### Установка зависимостей
```bash
# Установка Python 3.11+
sudo apt install python3.11 python3.11-venv python3.11-dev -y

# Установка PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Установка других зависимостей
sudo apt install build-essential libpq-dev -y
```

#### Настройка базы данных
```bash
# Вход в PostgreSQL
sudo -u postgres psql

# Создание пользователя и базы
CREATE USER arvlite_user WITH PASSWORD 'your_secure_password';
CREATE DATABASE arvlite_prod OWNER arvlite_user;
GRANT ALL PRIVILEGES ON DATABASE arvlite_prod TO arvlite_user;

# Выход из psql
\q
```

#### Создание systemd unit файлов

Создайте `/etc/systemd/system/arvlite-backend.service`:
```ini
[Unit]
Description=ARVlite Backend Service
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/arvlite/ARV
EnvironmentFile=/opt/arvlite/ARV/.env
ExecStart=/opt/arvlite/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Создайте `/etc/systemd/system/arvlite-frontend.service`:
```ini
[Unit]
Description=ARVlite Frontend Service
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/arvlite/ARV/frontend
ExecStart=/usr/bin/npm run serve
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Запуск сервисов
```bash
# Перезагрузка systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable arvlite-backend
sudo systemctl enable arvlite-frontend

# Запуск сервисов
sudo systemctl start arvlite-backend
sudo systemctl start arvlite-frontend

# Проверка статуса
sudo systemctl status arvlite-backend
sudo systemctl status arvlite-frontend
```

#### Логирование в journalctl
```bash
# Просмотр логов backend
sudo journalctl -u arvlite-backend -f

# Просмотр логов frontend
sudo journalctl -u arvlite-frontend -f

# Логи за последние 24 часа
sudo journalctl -u arvlite-backend --since "24 hours ago"
```

### 3. Nginx как reverse proxy

#### Установка и настройка Nginx
```bash
sudo apt install nginx -y
sudo systemctl enable nginx
sudo systemctl start nginx
```

#### Конфигурация домена
Создайте `/etc/nginx/sites-available/arvlite.conf`:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL сертификаты
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Настройки безопасности
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;

    # Frontend (React/Vue app)
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Статические файлы кэширование
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # WebSocket для уведомлений
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Заголовки безопасности
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
}
```

#### Активация конфигурации
```bash
sudo ln -s /etc/nginx/sites-available/arvlite.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### Получение SSL сертификата
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Автоматическое обновление сертификатов
sudo crontab -e
# Добавьте строку для еженедельной проверки:
0 12 * * 0 /usr/bin/certbot renew --quiet
```

## Мониторинг и логи

### Расположение логов
- **Docker**: `docker logs <container_name>`
- **Systemd**: `journalctl -u <service_name>`
- **Приложение**: `/var/log/arvlite/` (если настроено)
- **Nginx**: `/var/log/nginx/`

### Настройка логирования
В `.env` файлах настройте уровень логирования:
```
LOG_LEVEL=INFO
LOG_FILE=/var/log/arvlite/app.log
LOG_MAX_SIZE=10MB
LOG_BACKUP_COUNT=5
```

### Health checks
Проверка состояния приложения:
- Backend: `GET /api/health` (должен вернуть 200 OK)
- Frontend: `GET /` (должен вернуть 200 OK)
- База данных: `GET /api/health/db` (проверка подключения к БД)

### Метрики (Prometheus)
Если включены метрики:
- Endpoint: `GET /metrics`
- Порт: обычно 9090 или через тот же порт с префиксом `/metrics`

## Maintenance

### Обновление приложения
```bash
# Docker
cd /path/to/ARVlite/ARV
git pull origin main
docker-compose down
docker-compose up -d --build

# Systemd
cd /opt/arvlite/ARV
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
# Запустите миграции если нужно
alembic upgrade head
sudo systemctl restart arvlite-backend
```

### Backup и restore БД
#### Backup
```bash
# Docker
docker exec arvlite-db pg_dump -U arvlite_user arvlite_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# Systemd
pg_dump -h localhost -U arvlite_user arvlite_prod > backup_$(date +%Y%m%d_%H%M%S).sql
```

#### Restore
```bash
# Docker
cat backup.sql | docker exec -i arvlite-db psql -U arvlite_user arvlite_prod

# Systemd
psql -h localhost -U arvlite_user arvlite_prod < backup.sql
```

### Очистка старых логов
```bash
# Удаление логов старше 30 дней
find /var/log/arvlite -name "*.log" -mtime +30 -delete

# Сжатие логов
gzip /var/log/arvlite/*.log
```

## Security

### Firewall правила
```bash
# Установка UFW
sudo apt install ufw -y

# Настройка правил
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable

# Проверка статуса
sudo ufw status
```

### Управление секретами
- Не храните секреты в Git
- Используйте `.env` файлы вне репозитория
- Рассмотрите использование HashiCorp Vault для production

### JWT и токены
- Используйте надежные секретные ключи
- Устанавливайте короткий срок действия токенов
- Реализуйте механизм refresh token

### Rate limiting
Rate limiting уже встроен в приложение:
- 100 запросов в минуту на IP для общих эндпоинтов
- 10 запросов в минуту на IP для аутентификации
- Настройка в `app/middleware/rate_limiter.py`

## Заключение

После завершения установки:
1. Проверьте доступность сайта по домену
2. Протестируйте регистрацию/авторизацию
3. Проверьте работу всех основных функций
4. Настройте мониторинг и оповещения о падениях
5. Протестируйте восстановление из бэкапа

Для получения дополнительной информации см. документацию в `docs/` директории.