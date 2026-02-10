# Деплой Vertex AR на Cloud.ru (Ubuntu 24.04)

## Требования

- Сервер: Ubuntu 24.04 с публичным IP
- DNS: A-запись `ar.neuroimagen.ru` → публичный IP сервера
- Порты: 22 (SSH), 80 (HTTP), 443 (HTTPS) открыты

## Быстрый старт (одна команда)

### 1. Подключиться к серверу

```bash
ssh aruser@192.144.12.68
```

### 2. Скачать и запустить скрипт деплоя

```bash
# Скачиваем скрипт
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/nicktretyakov/ARV.git /tmp/arv-deploy
sudo bash /tmp/arv-deploy/scripts/deploy_cloudru.sh
```

Скрипт автоматически:
- Установит Python 3, PostgreSQL, Nginx, Redis, Certbot, ffmpeg
- Создаст пользователя `arv` и базу данных
- Склонирует репозиторий в `/opt/arv/app`
- Создаст виртуальное окружение и установит зависимости
- Настроит Nginx с HTTPS (Let's Encrypt)
- Запустит приложение через systemd

### 3. Сохранить креденшелы

В конце скрипт выведет:
- Пароль БД
- Пароль администратора
- Secret Key

**Обязательно сохраните их!**

## Ручной деплой (пошагово)

### 1. Системные пакеты

```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib libpq-dev \
    nginx certbot python3-certbot-nginx \
    redis-server ffmpeg git curl
```

### 2. Файрвол

```bash
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 3. PostgreSQL

```bash
sudo -u postgres psql -c "CREATE USER vertex_ar WITH PASSWORD 'YOUR_PASSWORD';"
sudo -u postgres psql -c "CREATE DATABASE vertex_ar OWNER vertex_ar;"
```

### 4. Пользователь приложения

```bash
sudo useradd --system --create-home --home-dir /opt/arv --shell /bin/bash arv
```

### 5. Код приложения

```bash
sudo -u arv git clone -b main https://github.com/nicktretyakov/ARV.git /opt/arv/app
```

### 6. Python окружение

```bash
sudo -u arv python3 -m venv /opt/arv/venv
sudo -u arv /opt/arv/venv/bin/pip install -r /opt/arv/app/requirements.txt
```

### 7. Конфигурация (.env)

```bash
sudo cp /opt/arv/app/.env.production /opt/arv/app/.env
sudo nano /opt/arv/app/.env
# Заполнить DATABASE_URL, SECRET_KEY, ADMIN_DEFAULT_PASSWORD
sudo chown arv:arv /opt/arv/app/.env
sudo chmod 600 /opt/arv/app/.env
```

### 8. Хранилище

```bash
sudo mkdir -p /opt/arv/storage/{content,thumbnails,markers,videos,temp}
sudo chown -R arv:arv /opt/arv/storage
```

### 9. Миграции

```bash
cd /opt/arv/app
sudo -u arv PYTHONPATH=/opt/arv/app /opt/arv/venv/bin/alembic upgrade head
```

### 10. Nginx

```bash
sudo cp /opt/arv/app/deploy/nginx/arv.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/arv.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx
```

### 11. SSL сертификат

```bash
sudo certbot --nginx -d ar.neuroimagen.ru --email admin@neuroimagen.ru --agree-tos
```

### 12. Systemd сервис

```bash
sudo cp /opt/arv/app/deploy/systemd/arv.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable arv
sudo systemctl start arv
```

## Управление

| Команда | Описание |
|---------|----------|
| `systemctl status arv` | Статус приложения |
| `systemctl restart arv` | Перезапуск |
| `systemctl stop arv` | Остановка |
| `journalctl -u arv -f` | Логи в реальном времени |
| `journalctl -u arv --since "1 hour ago"` | Логи за час |
| `sudo -u arv /opt/arv/venv/bin/alembic upgrade head` | Миграции |
| `sudo certbot renew --dry-run` | Проверка обновления SSL |

## Обновление кода

```bash
cd /opt/arv/app
sudo -u arv git pull origin main
sudo -u arv /opt/arv/venv/bin/pip install -r requirements.txt
sudo -u arv PYTHONPATH=/opt/arv/app /opt/arv/venv/bin/alembic upgrade head
sudo systemctl restart arv
```

## Структура на сервере

```
/opt/arv/
├── app/                    # Код приложения (git repo)
│   ├── app/                # Python package
│   ├── alembic/            # Миграции
│   ├── templates/          # HTML шаблоны
│   ├── static/             # CSS, JS
│   ├── deploy/             # Конфиги Nginx, systemd
│   ├── .env                # Конфигурация (секреты)
│   └── requirements.txt
├── venv/                   # Виртуальное окружение Python
└── storage/                # Загруженные файлы
    ├── content/
    ├── thumbnails/
    ├── markers/
    ├── videos/
    └── temp/
```

## DNS настройка

Убедитесь, что A-запись в DNS:

```
ar.neuroimagen.ru.  A  192.144.12.68
```

Проверка:
```bash
dig ar.neuroimagen.ru +short
# Должен вернуть: 192.144.12.68
```

## Проверка работоспособности

```bash
# С сервера:
curl -s http://localhost:8000/api/health | jq .

# Извне:
curl -s https://ar.neuroimagen.ru/api/health | jq .
```

## Устранение неполадок

### Приложение не запускается

```bash
journalctl -u arv -n 50 --no-pager
```

### Nginx ошибка

```bash
sudo nginx -t
sudo tail -20 /var/log/nginx/error.log
```

### PostgreSQL

```bash
sudo -u postgres psql -c "\l"       # Список БД
sudo -u postgres psql -d vertex_ar -c "\dt"  # Таблицы
```

### SSL не работает

```bash
sudo certbot certificates
sudo certbot renew --force-renewal
```
