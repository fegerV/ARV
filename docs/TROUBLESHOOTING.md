# Руководство по решению проблем

Документация по решению распространенных проблем в платформе ARV.

## Содержание

1. [Проблемы с базой данных](#проблемы-с-базой-данных)
2. [Проблемы с аутентификацией](#проблемы-с-аутентификацией)
3. [Проблемы с генерацией маркеров](#проблемы-с-генерацией-маркеров)
4. [Проблемы с Docker](#проблемы-с-docker)
5. [Проблемы с API](#проблемы-с-api)
6. [Проблемы с файлами и хранилищем](#проблемы-с-файлами-и-хранилищем)

## Проблемы с базой данных

### Ошибка: "Database is locked" (SQLite)

**Симптомы:**
- Приложение не может записать в базу данных
- Ошибки при применении миграций

**Решения:**

1. **Закройте все подключения к БД:**
   ```bash
   # Проверьте активные подключения
   lsof test_vertex_ar.db
   # Или на Windows
   # Закройте все программы, использующие БД
   ```

2. **Используйте PostgreSQL в продакшене:**
   ```bash
   export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/dbname"
   ```

3. **Перезапустите приложение:**
   ```bash
   docker compose restart
   ```

### Ошибка: "Table does not exist"

**Симптомы:**
- Ошибки при обращении к таблицам
- Миграции не применены

**Решения:**

1. **Примените миграции:**
   ```bash
   alembic upgrade head
   ```

2. **Проверьте текущую версию:**
   ```bash
   alembic current
   ```

3. **Просмотрите историю:**
   ```bash
   alembic history
   ```

### Ошибка при применении миграций

**Симптомы:**
- Миграции не применяются
- Ошибки в логах Alembic

**Решения:**

1. **Проверьте подключение к БД:**
   ```bash
   # Проверьте DATABASE_URL
   echo $DATABASE_URL
   ```

2. **Просмотрите SQL без применения:**
   ```bash
   alembic upgrade head --sql
   ```

3. **Откатите и примените заново:**
   ```bash
   alembic downgrade -1
   alembic upgrade head
   ```

## Проблемы с аутентификацией

### Не могу войти с правильным паролем

**Симптомы:**
- Ошибка "Неверный email или пароль" при правильных данных

**Решения:**

1. **Проверьте тип хеша пароля:**
   ```bash
   python utilities/check_hash_type.py
   ```

2. **Обновите пароль:**
   ```bash
   python utilities/update_password_directly.py
   ```

3. **Сбросьте пароль администратора:**
   ```bash
   python utilities/fix_admin_password.py
   ```

### Аккаунт заблокирован

**Симптомы:**
- Сообщение "Аккаунт временно заблокирован"
- Превышен лимит попыток входа

**Решения:**

1. **Подождите 15 минут** (стандартное время блокировки)

2. **Сбросьте блокировку:**
   ```bash
   python utilities/reset_login_attempts.py
   ```

3. **Или через SQL:**
   ```sql
   UPDATE users SET login_attempts = 0, locked_until = NULL WHERE email = 'admin@vertexar.com';
   ```

### Токен не принимается

**Симптомы:**
- Ошибка 401 Unauthorized при использовании токена
- Токен истек

**Решения:**

1. **Проверьте формат заголовка:**
   ```bash
   Authorization: Bearer <token>
   ```

2. **Проверьте SECRET_KEY:**
   - Должен быть одинаковым на всех серверах
   - Минимум 32 символа

3. **Проверьте время жизни токена:**
   - По умолчанию 24 часа
   - Настройка: `ACCESS_TOKEN_EXPIRE_MINUTES`

4. **Получите новый токен:**
   ```bash
   curl -X POST http://localhost:8000/api/auth/login \
     -d "username=admin@vertexar.com&password=your_password"
   ```

## Проблемы с генерацией маркеров

### Ошибка: "MindAR dependencies not found"

**Симптомы:**
- Ошибка при генерации маркеров
- Сообщение о отсутствующих зависимостях

**Решения:**

1. **Установите Node.js зависимости:**
   ```bash
   npm install
   ```

2. **Проверьте наличие пакетов:**
   ```bash
   ls node_modules/mind-ar
   ls node_modules/canvas
   ```

3. **В Docker:**
   ```dockerfile
   RUN npm install
   ```

### Ошибка: "Marker has no features"

**Симптомы:**
- Маркер создается, но не работает в AR viewer
- Предупреждение о отсутствии features

**Решения:**

1. **Используйте изображение с большим количеством деталей:**
   - Высокий контраст
   - Четкие границы
   - Уникальные паттерны

2. **Увеличьте max_features:**
   ```python
   MINDAR_MAX_FEATURES = 2000  # Вместо 1000
   ```

3. **Проверьте качество изображения:**
   - Минимум 640x480
   - Рекомендуется 1920x1080 или выше
   - Формат: JPEG или PNG

### Ошибка компиляции Node.js

**Симптомы:**
- Ошибки при выполнении mindar_compiler.mjs
- Timeout при генерации

**Решения:**

1. **Проверьте Node.js версию:**
   ```bash
   node --version  # Должна быть >= 18
   ```

2. **Проверьте системные зависимости для canvas:**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install build-essential libcairo2-dev libpango1.0-dev
   
   # macOS
   brew install pkg-config cairo pango
   ```

3. **Увеличьте timeout:**
   - В `mindar_generator.py` timeout = 300 секунд (5 минут)

## Проблемы с Docker

### Контейнер не запускается

**Симптомы:**
- Docker контейнер падает сразу после запуска
- Ошибки в логах

**Решения:**

1. **Проверьте логи:**
   ```bash
   docker compose logs app
   ```

2. **Проверьте переменные окружения:**
   ```bash
   docker compose config
   ```

3. **Пересоберите образ:**
   ```bash
   docker compose build --no-cache
   docker compose up
   ```

### База данных недоступна из контейнера

**Симптомы:**
- Ошибки подключения к БД
- Timeout при подключении

**Решения:**

1. **Проверьте, что PostgreSQL контейнер запущен:**
   ```bash
   docker compose ps
   ```

2. **Проверьте DATABASE_URL:**
   ```bash
   # Должен использовать имя сервиса из docker-compose.yml
   DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/dbname
   ```

3. **Проверьте сеть Docker:**
   ```bash
   docker network ls
   docker network inspect arv_default
   ```

### Проблемы с volumes

**Симптомы:**
- Файлы не сохраняются
- Ошибки доступа к файлам

**Решения:**

1. **Проверьте права доступа:**
   ```bash
   ls -la storage/
   ```

2. **Создайте директории:**
   ```bash
   mkdir -p storage/VertexAR
   chmod 755 storage
   ```

3. **Проверьте mount points в docker-compose.yml**

## Проблемы с API

### Ошибка 422: Validation Error

**Симптомы:**
- Запросы отклоняются с ошибкой валидации
- Неверный формат данных

**Решения:**

1. **Проверьте формат данных:**
   - Используйте правильные типы
   - Проверьте обязательные поля

2. **Проверьте документацию API:**
   ```bash
   # Откройте в браузере
   http://localhost:8000/docs
   ```

3. **Используйте примеры из docs/API_EXAMPLES.md**

### Ошибка 500: Internal Server Error

**Симптомы:**
- Внутренние ошибки сервера
- Неожиданные исключения

**Решения:**

1. **Проверьте логи приложения:**
   ```bash
   docker compose logs -f app
   ```

2. **Проверьте подключение к БД:**
   ```bash
   python utilities/check_db.py
   ```

3. **Проверьте доступность хранилища:**
   ```bash
   ls -la storage/
   ```

### CORS ошибки

**Симптомы:**
- Ошибки в браузере при запросах с другого домена
- "CORS policy" в консоли

**Решения:**

1. **Настройте CORS_ORIGINS:**
   ```python
   CORS_ORIGINS = [
       "http://localhost:3000",
       "https://yourdomain.com"
   ]
   ```

2. **Проверьте настройки в config.py**

3. **Для разработки можно разрешить все:**
   ```python
   CORS_ORIGINS = ["*"]  # Только для разработки!
   ```

## Проблемы с файлами и хранилищем

### Файлы не загружаются

**Симптомы:**
- Ошибки при загрузке файлов
- Файлы не сохраняются

**Решения:**

1. **Проверьте права доступа:**
   ```bash
   ls -la storage/
   chmod 755 storage/
   ```

2. **Проверьте размер файлов:**
   - Фото: максимум 10MB
   - Видео: максимум 100MB

3. **Проверьте формат файлов:**
   - Фото: JPEG, PNG
   - Видео: MP4, WebM, MOV

### Файлы не отображаются

**Симптомы:**
- Файлы загружены, но не видны
- Ошибки 404 при доступе к файлам

**Решения:**

1. **Проверьте PUBLIC_URL:**
   ```python
   PUBLIC_URL = "http://localhost:8000"
   ```

2. **Проверьте маршруты статических файлов:**
   ```python
   # В main.py должны быть настроены static routes
   ```

3. **Проверьте путь к файлам:**
   ```bash
   ls -la storage/VertexAR/
   ```

### Недостаточно места на диске

**Симптомы:**
- Ошибки при сохранении файлов
- "No space left on device"

**Решения:**

1. **Проверьте свободное место:**
   ```bash
   df -h
   ```

2. **Очистите старые файлы:**
   ```bash
   # Удалите неиспользуемые файлы
   find storage/ -type f -mtime +30 -delete
   ```

3. **Настройте автоматическую очистку**

## Общие советы

### Просмотр логов

```bash
# Docker
docker compose logs -f app

# Локально
tail -f logs/app.log
```

### Проверка конфигурации

```bash
# Проверьте переменные окружения
env | grep -E "(DATABASE|SECRET|CORS)"

# Проверьте настройки в config.py
python -c "from app.core.config import settings; print(settings.dict())"
```

### Тестирование подключений

```bash
# База данных
python utilities/check_db.py

# Пользователи
python utilities/check_users_and_auth.py

# Миграции
python utilities/check_migration.py
```

### Сброс к начальному состоянию

```bash
# Осторожно! Удалит все данные
rm -rf storage/*
rm test_vertex_ar.db
alembic upgrade head
python utilities/create_admin.py
```

## Получение помощи

Если проблема не решена:

1. Проверьте логи приложения
2. Изучите документацию API: http://localhost:8000/docs
3. Создайте issue в репозитории с описанием проблемы
4. Приложите логи и конфигурацию (без секретных данных)
