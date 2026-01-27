# Описание сервисов

Подробное описание всех сервисов платформы ARV и их взаимодействия.

## Обзор

Платформа использует сервис-ориентированную архитектуру, где бизнес-логика вынесена в отдельные сервисы. Это обеспечивает модульность, тестируемость и переиспользование кода.

## Архитектура сервисов

```
API Routes → Services → Models → Database
                ↓
         External Services
```

## Основные сервисы

### 1. MindARGenerator

**Файл**: `app/services/mindar_generator.py`

**Назначение**: Генерация AR-маркеров из изображений

**Основные методы:**

- `generate_marker()` - Генерация .mind файла из изображения
- `validate_marker_file()` - Валидация созданного маркера
- `generate_and_upload_marker()` - Генерация и сохранение маркера

**Использование:**
```python
from app.services.mindar_generator import mindar_generator

result = await mindar_generator.generate_and_upload_marker(
    ar_content_id="123",
    image_path=Path("photo.jpg"),
    max_features=1000,
    storage_path=Path("storage/path")
)
```

**Зависимости:**
- Node.js (mind-ar, canvas)
- Pillow для работы с изображениями

**Особенности:**
- Асинхронная генерация через subprocess
- Валидация маркеров
- Fallback режим при ошибках

### 2. MindARMarkerService

**Файл**: `app/services/marker_service.py`

**Назначение**: Высокоуровневый сервис для работы с маркерами

**Основные методы:**

- `generate_marker()` - Генерация маркера с анализом качества
- `analyze_image_quality()` - Анализ качества изображения
- `build_image_recommendations()` - Рекомендации по улучшению

**Использование:**
```python
from app.services.marker_service import MindARMarkerService

service = MindARMarkerService()
result = await service.generate_marker(
    ar_content_id=1,
    image_path="photo.jpg",
    storage_path=Path("storage/path")
)
```

**Особенности:**
- Интеграция с MindARGenerator
- Анализ качества изображений
- Рекомендации по улучшению

### 3. ThumbnailService

**Файл**: `app/services/thumbnail_service.py`

**Назначение**: Генерация превью изображений и видео

**Основные методы:**

- `generate_thumbnail()` - Генерация превью
- `generate_video_thumbnail()` - Превью для видео

**Использование:**
```python
from app.services.thumbnail_service import ThumbnailService

service = ThumbnailService()
thumbnail_path = await service.generate_thumbnail(
    image_path="photo.jpg",
    output_path="thumbnail.webp",
    size=(300, 300)
)
```

**Зависимости:**
- Pillow для изображений
- OpenCV для видео

### 4. EnhancedThumbnailService

**Файл**: `app/services/enhanced_thumbnail_service.py`

**Назначение**: Расширенный сервис генерации превью с оптимизацией

**Основные методы:**

- `generate_optimized_thumbnail()` - Оптимизированное превью
- `generate_multiple_sizes()` - Генерация нескольких размеров
- `batch_generate()` - Пакетная генерация

**Особенности:**
- Поддержка WebP
- Автоматическая оптимизация
- Пакетная обработка

### 5. VideoScheduler

**Файл**: `app/services/video_scheduler.py`

**Назначение**: Логика выбора и ротации видео для AR-контента

**Основные методы:**

- `get_active_video()` - Получение активного видео с приоритетами
- `get_next_rotation_video()` - Следующее видео в ротации
- `update_rotation_state()` - Обновление состояния ротации
- `get_videos_with_active_schedules()` - Видео с активным расписанием

**Приоритеты выбора:**

1. Видео с активным расписанием
2. Активное видео по `active_video_id`
3. Ротация (sequential/cyclic)
4. Fallback: любое активное видео

**Режимы ротации:**

- `none` - Фиксированное видео
- `sequential` - Последовательное переключение
- `cyclic` - Циклическое переключение

**Использование:**
```python
from app.services.video_scheduler import get_active_video

result = await get_active_video(ar_content_id=1, db=db)
video = result["video"]
source = result["source"]  # "schedule", "active_default", "rotation", "fallback"
```

### 6. NotificationService

**Файл**: `app/services/notification_service.py`

**Назначение**: Отправка уведомлений (email, Telegram)

**Основные методы:**

- `send_notification()` - Отправка уведомления
- `send_email()` - Отправка email
- `send_telegram()` - Отправка в Telegram

**Использование:**
```python
from app.services.notification_service import NotificationService

service = NotificationService()
await service.send_notification(
    notification_type="ar_content_created",
    subject="Новый AR-контент",
    message="Создан новый AR-контент",
    company_id=1
)
```

**Зависимости:**
- SMTP для email
- Telegram Bot API

### 7. SettingsService

**Файл**: `app/services/settings_service.py`

**Назначение**: Управление настройками системы

**Основные методы:**

- `get_settings()` - Получение настроек
- `update_settings()` - Обновление настроек
- `get_setting()` - Получение одной настройки
- `set_setting()` - Установка настройки

**Использование:**
```python
from app.services.settings_service import SettingsService

service = SettingsService(db)
settings = await service.get_settings(category="general")
await service.set_setting("api_keys_enabled", "true", "boolean")
```

**Категории настроек:**
- `general` - Общие настройки
- `storage` - Настройки хранилища
- `notifications` - Настройки уведомлений
- `api` - Настройки API
- `integrations` - Настройки интеграций
- `ar` - Настройки AR

### 8. EnhancedCacheService

**Файл**: `app/services/enhanced_cache_service.py`

**Назначение**: Многоуровневое кэширование

**Уровни кэширования:**

1. **L1 - Memory Cache** - In-memory LRU кэш
2. **L2 - Redis Cache** - Распределенное кэширование
3. **L3 - Disk Cache** - Долгосрочное хранение
4. **L4 - CDN** - Глобальное кэширование (планируется)

**Стратегии кэширования:**

- `LAZY` - Загрузка по требованию
- `EAGER` - Предзагрузка
- `WRITE_THROUGH` - Запись во все уровни
- `WRITE_BACK` - Запись в L1, асинхронно в другие

**Использование:**
```python
from app.services.enhanced_cache_service import EnhancedCacheService

cache = EnhancedCacheService()

# Получить из кэша
value = await cache.get("key", cache_type="metadata")

# Сохранить в кэш
await cache.set("key", value, cache_type="metadata", ttl=3600)
```

**Типы кэша:**
- `thumbnails` - Превью (L1, 1 час)
- `metadata` - Метаданные (L2, 2 часа)
- `media_info` - Информация о медиа (L3, 24 часа)
- `api_responses` - Ответы API (L2, 5 минут)
- `user_sessions` - Сессии пользователей (L2, 30 минут)

### 9. ReliabilityService

**Файл**: `app/services/reliability_service.py`

**Назначение**: Обеспечение надежности через Circuit Breaker и Retry

**Компоненты:**

1. **CircuitBreaker** - Защита от каскадных сбоев
2. **Retry** - Повторные попытки при ошибках
3. **HealthCheck** - Проверка здоровья сервисов

**Использование:**
```python
from app.services.reliability_service import (
    CircuitBreaker, CircuitBreakerConfig,
    Retry, RetryConfig, RetryStrategy
)

# Circuit Breaker
breaker_config = CircuitBreakerConfig(
    failure_threshold=5,
    timeout=60,
    success_threshold=3
)
breaker = CircuitBreaker("external_api", breaker_config)

@breaker
async def call_external_api():
    # Вызов внешнего API
    pass

# Retry
retry_config = RetryConfig(
    max_attempts=3,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    base_delay=1.0
)
retry = Retry("database_operation", retry_config)

@retry
async def database_operation():
    # Операция с БД
    pass
```

**Состояния Circuit Breaker:**
- `CLOSED` - Нормальная работа
- `OPEN` - Цепь разомкнута, запросы отклоняются
- `HALF_OPEN` - Тестирование восстановления

### 10. AlertService

**Файл**: `app/services/alert_service.py`

**Назначение**: Отправка алертов о критических событиях

**Основные методы:**

- `send_critical_alerts()` - Отправка критических алертов
- `send_admin_email()` - Email администраторам
- `send_telegram_alerts()` - Telegram алерты

**Уровни серьезности:**
- `critical` - Критические (cooldown 5 минут)
- `warning` - Предупреждения (cooldown 15 минут)
- `info` - Информационные (cooldown 1 час)

**Использование:**
```python
from app.services.alert_service import Alert, send_critical_alerts

alerts = [
    Alert(
        severity="critical",
        title="Database connection failed",
        message="Cannot connect to database",
        metrics={"error_count": 10},
        affected_services=["database"]
    )
]

await send_critical_alerts(alerts, metrics={})
```

### 11. BackupBotService

**Файл**: `app/services/backup_bot.py`

**Назначение**: Автоматическое резервное копирование

**Основные методы:**

- `create_backup()` - Создание бэкапа
- `upload_to_s3()` - Загрузка в S3
- `cleanup_old_backups()` - Очистка старых бэкапов

**Использование:**
```python
from app.services.backup_bot import BackupBotService

service = BackupBotService()
await service.create_backup()
```

### 12. EnhancedValidationService

**Файл**: `app/services/enhanced_validation_service.py`

**Назначение**: Расширенная валидация данных

**Основные методы:**

- `validate_ar_content()` - Валидация AR-контента
- `validate_file()` - Валидация файлов
- `validate_video()` - Валидация видео

**Особенности:**
- Проверка типов файлов
- Проверка размеров
- Проверка форматов

## Взаимодействие сервисов

### Создание AR-контента

```
API Route (ar_content.py)
    ↓
1. ValidationService → Валидация данных
    ↓
2. Storage Provider → Сохранение файлов
    ↓
3. ThumbnailService → Генерация превью
    ↓
4. MindARGenerator → Генерация маркера
    ↓
5. NotificationService → Уведомление о создании
    ↓
6. Cache Service → Инвалидация кэша
```

### Просмотр AR-контента

```
Viewer Route
    ↓
1. Cache Service → Проверка кэша
    ↓
2. VideoScheduler → Выбор активного видео
    ↓
3. Storage Provider → Получение файлов
    ↓
4. Cache Service → Сохранение в кэш
```

## Зависимости между сервисами

```
MindARGenerator
    ↓ (использует)
Storage Provider

VideoScheduler
    ↓ (использует)
Database Models

NotificationService
    ↓ (использует)
SMTP / Telegram API

EnhancedCacheService
    ↓ (использует)
Redis (опционально)

ReliabilityService
    ↓ (оборачивает)
Другие сервисы
```

## Best Practices

### 1. Dependency Injection

```python
from fastapi import Depends

def get_video_scheduler():
    return VideoScheduler()

@router.get("/video/")
async def get_video(
    scheduler: VideoScheduler = Depends(get_video_scheduler)
):
    return await scheduler.get_active_video(...)
```

### 2. Логирование

```python
import structlog

logger = structlog.get_logger()

class MyService:
    async def do_something(self):
        logger.info("service_operation_started", service="MyService")
        try:
            result = await self._process()
            logger.info("service_operation_completed", result=result)
            return result
        except Exception as e:
            logger.error("service_operation_failed", error=str(e))
            raise
```

### 3. Обработка ошибок

```python
class ServiceError(Exception):
    """Base exception for services"""
    pass

class MarkerGenerationError(ServiceError):
    """Error during marker generation"""
    pass

async def generate_marker(...):
    try:
        result = await mindar_generator.generate(...)
        return result
    except Exception as e:
        raise MarkerGenerationError(f"Failed to generate marker: {e}")
```

### 4. Тестирование

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_video_scheduler():
    with patch('app.services.video_scheduler.get_db') as mock_db:
        mock_db.return_value = AsyncMock()
        
        result = await get_active_video(ar_content_id=1, db=mock_db)
        
        assert result is not None
        assert "video" in result
```

## Расширение сервисов

### Добавление нового сервиса

1. **Создайте файл сервиса:**
   ```python
   # app/services/my_service.py
   import structlog
   
   logger = structlog.get_logger()
   
   class MyService:
       async def do_something(self):
           logger.info("doing_something")
           # Логика сервиса
   ```

2. **Используйте в routes:**
   ```python
   from app.services.my_service import MyService
   
   @router.get("/endpoint/")
   async def endpoint(service: MyService = Depends(get_my_service)):
       return await service.do_something()
   ```

3. **Добавьте тесты:**
   ```python
   # tests/test_my_service.py
   def test_my_service():
       service = MyService()
       result = await service.do_something()
       assert result is not None
   ```

## Мониторинг сервисов

### Метрики

Все сервисы должны экспортировать метрики:

```python
from prometheus_client import Counter, Histogram

SERVICE_OPERATIONS = Counter(
    'service_operations_total',
    'Total service operations',
    ['service', 'operation', 'status']
)

SERVICE_DURATION = Histogram(
    'service_operation_duration_seconds',
    'Service operation duration',
    ['service', 'operation']
)
```

### Health Checks

```python
async def health_check() -> dict:
    return {
        "status": "healthy",
        "services": {
            "database": await check_database(),
            "cache": await check_cache(),
            "storage": await check_storage()
        }
    }
```

## Дополнительные ресурсы

- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [Service-Oriented Architecture](https://martinfowler.com/articles/microservices.html)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
