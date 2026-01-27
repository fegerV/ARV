# Политика безопасности

Подробное руководство по безопасности платформы ARV для продакшена.

## Обзор

Этот документ описывает меры безопасности, реализованные в платформе ARV, и рекомендации по их настройке для продакшена.

## Аутентификация и авторизация

### JWT токены

**Текущая реализация:**
- Алгоритм: HS256
- Время жизни: 24 часа (настраивается)
- Хранение: HTTP-only cookies (HTML) или Bearer token (API)

**Рекомендации для продакшена:**

1. **Используйте сильный SECRET_KEY:**
   ```bash
   # Генерация случайного ключа
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   
   Установите в `.env`:
   ```bash
   SECRET_KEY=your-generated-secret-key-min-32-chars
   ```

2. **Сократите время жизни токенов:**
   ```python
   ACCESS_TOKEN_EXPIRE_MINUTES=60  # 1 час вместо 24
   ```

3. **Используйте HTTPS:**
   - Всегда используйте HTTPS в продакшене
   - Настройте редирект с HTTP на HTTPS
   - Используйте HSTS заголовки

4. **Реализуйте refresh tokens** (планируется):
   - Короткоживущие access tokens (15 минут)
   - Долгоживущие refresh tokens (7 дней)
   - Ротация refresh tokens

### Хеширование паролей

**Текущая реализация:**
- Алгоритм: SHA-256
- Формат: Hex-строка

**⚠️ ВАЖНО: SHA-256 не рекомендуется для паролей!**

**Рекомендации:**

1. **Используйте bcrypt или Argon2:**
   ```python
   from passlib.context import CryptContext
   
   pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
   
   def get_password_hash(password: str) -> str:
       return pwd_context.hash(password)
   
   def verify_password(plain_password: str, hashed_password: str) -> bool:
       return pwd_context.verify(plain_password, hashed_password)
   ```

2. **Требования к паролям:**
   - Минимум 12 символов
   - Содержит заглавные и строчные буквы
   - Содержит цифры
   - Содержит специальные символы
   - Не является распространенным паролем

### Защита от брутфорса

**Текущая реализация:**
- Максимум 5 неудачных попыток
- Блокировка на 15 минут
- Rate limiting: 10 попыток в минуту на IP

**Рекомендации:**

1. **Увеличьте время блокировки:**
   ```python
   LOCKOUT_DURATION = timedelta(minutes=30)  # Вместо 15
   ```

2. **Используйте CAPTCHA** после 3 неудачных попыток

3. **Логируйте все попытки входа:**
   - Успешные и неуспешные
   - IP адреса
   - User agents
   - Время попыток

## Защита API

### Rate Limiting

**Текущая реализация:**
- Аутентифицированные пользователи: 100 запросов в час
- Неаутентифицированные: 100 запросов в минуту
- Используется slowapi

**Рекомендации:**

1. **Настройте лимиты по endpoint:**
   ```python
   @rate_limit(max_requests=10, window_size="minute", per_user=True)
   @router.post("/api/ar-content/")
   async def create_ar_content(...):
       ...
   ```

2. **Используйте Redis для распределенного rate limiting:**
   - Для нескольких инстансов приложения
   - Для синхронизации лимитов между серверами

3. **Добавьте заголовки rate limit:**
   - `X-RateLimit-Limit`
   - `X-RateLimit-Remaining`
   - `X-RateLimit-Reset`

### CORS

**Текущая реализация:**
- Настраивается через `CORS_ORIGINS`
- Поддержка credentials

**Рекомендации:**

1. **Ограничьте разрешенные домены:**
   ```python
   CORS_ORIGINS = [
       "https://yourdomain.com",
       "https://admin.yourdomain.com"
   ]
   ```

2. **Не используйте `*` в продакшене:**
   ```python
   # ПЛОХО
   CORS_ORIGINS = ["*"]
   
   # ХОРОШО
   CORS_ORIGINS = ["https://yourdomain.com"]
   ```

3. **Настройте CORS заголовки:**
   ```python
   allow_credentials=True,
   allow_methods=["GET", "POST", "PUT", "DELETE"],
   allow_headers=["Authorization", "Content-Type"],
   max_age=3600
   ```

### Валидация входных данных

**Текущая реализация:**
- Pydantic схемы для валидации
- Автоматическая валидация типов

**Рекомендации:**

1. **Валидируйте все входные данные:**
   ```python
   from pydantic import BaseModel, validator, EmailStr
   
   class UserCreate(BaseModel):
       email: EmailStr
       password: str
       
       @validator('password')
       def validate_password(cls, v):
           if len(v) < 12:
               raise ValueError('Password must be at least 12 characters')
           return v
   ```

2. **Ограничивайте размер файлов:**
   ```python
   MAX_FILE_SIZE_PHOTO = 10 * 1024 * 1024  # 10MB
   MAX_FILE_SIZE_VIDEO = 100 * 1024 * 1024  # 100MB
   ```

3. **Проверяйте типы файлов:**
   ```python
   ALLOWED_FILE_EXTENSIONS_PHOTO = ["jpeg", "jpg", "png"]
   ALLOWED_FILE_EXTENSIONS_VIDEO = ["mp4", "webm", "mov"]
   ```

## Защита от атак

### SQL Injection

**Защита:**
- Использование SQLAlchemy ORM
- Параметризованные запросы
- Нет прямых SQL запросов

**Рекомендации:**

1. **Никогда не используйте f-строки для SQL:**
   ```python
   # ПЛОХО
   query = f"SELECT * FROM users WHERE email = '{email}'"
   
   # ХОРОШО
   stmt = select(User).where(User.email == email)
   ```

2. **Используйте prepared statements:**
   - SQLAlchemy делает это автоматически
   - Всегда используйте ORM методы

### XSS (Cross-Site Scripting)

**Защита:**
- Экранирование в Jinja2 шаблонах
- Автоматическое экранирование по умолчанию

**Рекомендации:**

1. **Используйте `|e` фильтр в шаблонах:**
   ```jinja2
   {{ user_input|e }}
   ```

2. **Настройте Content Security Policy:**
   ```python
   @app.middleware("http")
   async def add_security_headers(request: Request, call_next):
       response = await call_next(request)
       response.headers["Content-Security-Policy"] = (
           "default-src 'self'; "
           "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
           "style-src 'self' 'unsafe-inline';"
       )
       return response
   ```

3. **Валидируйте и санитизируйте пользовательский ввод**

### CSRF (Cross-Site Request Forgery)

**Текущее состояние:**
- Не реализовано

**Рекомендации:**

1. **Используйте CSRF токены:**
   ```python
   from fastapi_csrf_protect import CsrfProtect
   
   @app.post("/api/ar-content/")
   async def create_ar_content(
       csrf_protect: CsrfProtect = Depends(),
       ...
   ):
       await csrf_protect.validate_csrf(request)
       ...
   ```

2. **Используйте SameSite cookies:**
   ```python
   response.set_cookie(
       key="access_token",
       value=token,
       samesite="strict",  # или "lax"
       secure=True,
       httponly=True
   )
   ```

### Path Traversal

**Защита:**
- Валидация путей в storage providers
- Использование Path объектов

**Рекомендации:**

1. **Проверяйте пути на выход за пределы базовой директории:**
   ```python
   def _get_full_path(self, storage_path: str) -> Path:
       storage_path = storage_path.lstrip('/')
       full_path = self.base_path / storage_path
       
       # Проверка на path traversal
       if not str(full_path.resolve()).startswith(str(self.base_path.resolve())):
           raise ValueError("Invalid path")
       
       return full_path
   ```

2. **Санитизируйте имена файлов:**
   ```python
   def sanitize_filename(name: str) -> str:
       # Удаляем опасные символы
       name = re.sub(r'[<>:"/\\|?*\x00]', '', name)
       return name
   ```

## Безопасность данных

### Шифрование

**Рекомендации:**

1. **Шифруйте чувствительные данные в БД:**
   - Пароли (уже хешируются)
   - API ключи
   - Токены доступа

2. **Используйте шифрование на уровне приложения:**
   ```python
   from cryptography.fernet import Fernet
   
   key = Fernet.generate_key()
   cipher = Fernet(key)
   
   encrypted = cipher.encrypt(b"sensitive data")
   decrypted = cipher.decrypt(encrypted)
   ```

3. **Используйте TLS для передачи данных:**
   - HTTPS для всех соединений
   - TLS 1.2+ для API
   - Проверка сертификатов

### Резервное копирование

**Рекомендации:**

1. **Регулярные бэкапы БД:**
   ```bash
   # Ежедневные бэкапы
   0 2 * * * pg_dump database > backup_$(date +\%Y\%m\%d).sql
   ```

2. **Шифруйте бэкапы:**
   ```bash
   pg_dump database | gzip | openssl enc -aes-256-cbc > backup.sql.gz.enc
   ```

3. **Храните бэкапы в безопасном месте:**
   - Отдельный сервер
   - Облачное хранилище с шифрованием
   - Регулярное тестирование восстановления

## Безопасность инфраструктуры

### Переменные окружения

**Рекомендации:**

1. **Никогда не коммитьте секреты в Git:**
   ```bash
   # .gitignore
   .env
   .env.local
   .env.production
   ```

2. **Используйте секретные менеджеры:**
   - AWS Secrets Manager
   - HashiCorp Vault
   - Kubernetes Secrets

3. **Ротация секретов:**
   - Регулярная смена SECRET_KEY
   - Ротация API ключей
   - Обновление паролей БД

### Docker

**Рекомендации:**

1. **Используйте non-root пользователя:**
   ```dockerfile
   RUN adduser --disabled-password --gecos '' appuser
   USER appuser
   ```

2. **Минимизируйте образ:**
   ```dockerfile
   FROM python:3.11-slim
   # Используйте multi-stage builds
   ```

3. **Сканируйте образы на уязвимости:**
   ```bash
   docker scan your-image
   ```

4. **Не храните секреты в образах:**
   - Используйте переменные окружения
   - Используйте Docker secrets

### Сетевая безопасность

**Рекомендации:**

1. **Используйте firewall:**
   - Откройте только необходимые порты
   - Блокируйте входящие соединения по умолчанию

2. **Используйте VPN для админ-доступа:**
   - Не открывайте админ-панель публично
   - Используйте VPN или SSH туннель

3. **Настройте DDoS защиту:**
   - Cloudflare
   - AWS Shield
   - Rate limiting на уровне Nginx

## Мониторинг и аудит

### Логирование

**Рекомендации:**

1. **Логируйте все важные события:**
   - Попытки входа (успешные и неуспешные)
   - Изменения данных
   - Ошибки безопасности
   - Доступ к чувствительным данным

2. **Не логируйте чувствительные данные:**
   ```python
   # ПЛОХО
   logger.info("user_login", password=password)
   
   # ХОРОШО
   logger.info("user_login", user_id=user.id, email=user.email)
   ```

3. **Централизованное логирование:**
   - ELK Stack (Elasticsearch, Logstash, Kibana)
   - CloudWatch
   - Sentry для ошибок

### Аудит

**Рекомендации:**

1. **Ведите аудит-логи:**
   ```python
   class AuditLog(Base):
       user_id: int
       action: str
       resource_type: str
       resource_id: int
       ip_address: str
       user_agent: str
       timestamp: datetime
   ```

2. **Отслеживайте подозрительную активность:**
   - Множественные неудачные попытки входа
   - Необычные паттерны доступа
   - Изменения в критичных данных

3. **Регулярные проверки безопасности:**
   - Аудит кода
   - Пентесты
   - Сканирование уязвимостей

## Чек-лист безопасности для продакшена

### Перед развертыванием

- [ ] Изменен SECRET_KEY на случайную строку (32+ символов)
- [ ] Изменен ADMIN_DEFAULT_PASSWORD
- [ ] Настроен HTTPS
- [ ] Настроены правильные CORS_ORIGINS
- [ ] Включен DEBUG=false
- [ ] Настроено логирование
- [ ] Настроен firewall
- [ ] Настроены резервные копии
- [ ] Проверены права доступа к файлам
- [ ] Обновлены все зависимости

### Регулярные проверки

- [ ] Обновление зависимостей (еженедельно)
- [ ] Проверка логов на подозрительную активность (ежедневно)
- [ ] Тестирование восстановления из бэкапа (ежемесячно)
- [ ] Аудит безопасности (ежеквартально)
- [ ] Пентесты (ежегодно)

## Дополнительные ресурсы

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/secrets.html)

## Контакты для сообщений об уязвимостях

Если вы обнаружили уязвимость безопасности, пожалуйста, сообщите об этом:
- Email: security@vertexar.com
- Не публикуйте уязвимости публично до исправления
