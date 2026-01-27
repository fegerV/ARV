# Система аутентификации

Документация по системе аутентификации и авторизации в платформе ARV.

## Обзор

Платформа использует JWT (JSON Web Tokens) для аутентификации пользователей. Система поддерживает защиту от брутфорса, блокировку аккаунтов и безопасное хранение паролей.

## Компоненты системы

### 1. JWT токены

- **Алгоритм**: HS256
- **Время жизни**: Настраивается через `ACCESS_TOKEN_EXPIRE_MINUTES` (по умолчанию 1440 минут = 24 часа)
- **Секретный ключ**: Настраивается через переменную окружения `SECRET_KEY`
- **Содержимое токена**: `sub` (email пользователя), `user_id`, `exp` (время истечения)

### 2. Хеширование паролей

- **Алгоритм**: SHA-256
- **Реализация**: Простое хеширование через `hashlib.sha256()`
- **Формат**: Hex-строка (64 символа)

**Пример:**
```python
import hashlib
hashed = hashlib.sha256("password".encode()).hexdigest()
```

### 3. Защита от брутфорса

- **Максимум попыток**: 5 неудачных попыток входа
- **Блокировка**: 15 минут после превышения лимита
- **Счетчик попыток**: Сбрасывается при успешном входе
- **Rate limiting**: 10 попыток входа в минуту на IP-адрес

## API Endpoints

### POST `/api/auth/login`

Аутентификация пользователя через API.

**Параметры:**
- `username` (form-data): Email пользователя
- `password` (form-data): Пароль

**Ответ при успехе:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "admin@vertexar.com",
    "is_active": true,
    "role": "admin"
  }
}
```

**Ошибки:**
- `401 Unauthorized`: Неверный email или пароль
- `403 Forbidden`: Аккаунт заблокирован (превышен лимит попыток)

### POST `/auth/login-form`

Аутентификация через HTML форму (для админ-панели).

**Параметры:**
- `username` (form-data): Email пользователя
- `password` (form-data): Пароль

**Ответ:** Редирект на `/admin` с установленным HTTP-only cookie `access_token`

### POST `/api/auth/logout`

Выход из системы (JWT stateless, просто логирует событие).

**Требования:** Токен в заголовке `Authorization: Bearer <token>`

## Использование токенов

### В API запросах

Добавьте токен в заголовок `Authorization`:

```bash
curl -H "Authorization: Bearer <your-token>" \
     http://localhost:8000/api/ar-content/
```

### В HTML формах

При использовании HTML форм токен автоматически устанавливается в HTTP-only cookie и отправляется с каждым запросом.

## Модель пользователя

### Поля безопасности

- `email`: Уникальный email пользователя
- `hashed_password`: SHA-256 хеш пароля
- `is_active`: Флаг активности аккаунта
- `role`: Роль пользователя (admin, user, etc.)
- `login_attempts`: Счетчик неудачных попыток входа
- `locked_until`: Время до разблокировки аккаунта (если заблокирован)
- `last_login_at`: Время последнего успешного входа

## Зависимости

### Python

- `python-jose[cryptography]`: Для работы с JWT токенами
- `hashlib`: Для хеширования паролей (встроенная библиотека)

### Конфигурация

Настройки в `app/core/config.py`:

```python
SECRET_KEY: str = "change-this-to-a-secure-random-key-min-32-chars"
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 часа
```

## Безопасность

### Рекомендации для продакшена

1. **SECRET_KEY**: Обязательно измените на случайную строку минимум 32 символа
2. **HTTPS**: Используйте HTTPS в продакшене для защиты токенов
3. **HTTP-only cookies**: Используются для защиты от XSS атак
4. **CORS**: Настройте правильно для вашего домена
5. **Rate limiting**: Уже реализован на уровне endpoint

### Валидация паролей

Требования к паролям (если реализованы):
- Минимум 8 символов
- Содержит заглавные и строчные буквы
- Содержит цифры

## Утилиты

В папке `utilities/` доступны скрипты для работы с паролями:

- `create_admin.py`: Создание администратора
- `fix_admin_password.py`: Сброс пароля администратора
- `update_password_directly.py`: Прямое обновление пароля в БД
- `check_hash_type.py`: Проверка типа хеша пароля

## Примеры использования

### Создание токена программно

```python
from app.core.security import create_access_token
from datetime import timedelta

token = create_access_token(
    data={"sub": "user@example.com", "user_id": 1},
    expires_delta=timedelta(hours=1)
)
```

### Проверка пароля

```python
from app.core.security import verify_password, get_password_hash

# Хеширование
hashed = get_password_hash("my_password")

# Проверка
is_valid = verify_password("my_password", hashed)
```

### Получение текущего пользователя

```python
from app.api.dependencies import get_current_active_user

@router.get("/protected")
async def protected_route(current_user: User = Depends(get_current_active_user)):
    return {"user_id": current_user.id, "email": current_user.email}
```

## Troubleshooting

### Проблема: Токен не принимается

**Решение:**
1. Проверьте, что `SECRET_KEY` одинаковый на всех серверах
2. Убедитесь, что токен не истек
3. Проверьте формат заголовка: `Authorization: Bearer <token>`

### Проблема: Аккаунт заблокирован

**Решение:**
1. Подождите 15 минут
2. Или сбросьте через скрипт: `python utilities/reset_login_attempts.py`

### Проблема: Не могу войти с правильным паролем

**Решение:**
1. Проверьте тип хеша: `python utilities/check_hash_type.py`
2. Если хеш не SHA-256, обновите: `python utilities/update_password_directly.py`
