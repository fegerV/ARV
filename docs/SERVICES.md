# Сервисы платформы ARV

Бизнес-логика вынесена в сервисный слой (`app/services/`). Маршруты обращаются к сервисам, а не работают с БД напрямую.

```
API / HTML Routes → Services → Models → Database
                       ↓
                 External APIs (YD, SMTP, Telegram)
```

## Реестр сервисов

| Файл | Класс / функция | Назначение |
|------|-----------------|-----------|
| `backup_service.py` | `BackupService` | Бэкап PostgreSQL → gzip → Яндекс Диск |
| `settings_service.py` | `SettingsService` | CRUD настроек из `system_settings` |
| `thumbnail_service.py` | `thumbnail_service` | Генерация превью (фото и видео) |
| `enhanced_thumbnail_service.py` | `EnhancedThumbnailService` | Мульти-размерные WebP превью |
| `video_scheduler.py` | `get_active_video()` | Выбор активного видео (ротация) |
| `marker_service.py` | `marker_service` | AR-маркеры (фото = маркер для ARCore) |
| `notification_service.py` | `notification_service` | Уведомления (email, Telegram) |
| `enhanced_validation_service.py` | `EnhancedValidationService` | Расширенная валидация файлов |
| `enhanced_cache_service.py` | `EnhancedCacheService` | Многоуровневое кэширование |
| `reliability_service.py` | `CircuitBreaker`, `Retry` | Circuit Breaker + Retry |
| `alert_service.py` | `alert_service` | Алерты (critical, warning, info) |
| `storage.py` | Утилиты хранилища | Вспомогательные функции для хранилища |

## Ключевые сервисы

### BackupService

**Файл**: `app/services/backup_service.py`

Автоматическое резервное копирование PostgreSQL на Яндекс Диск.

**Алгоритм:**
1. Парсинг DATABASE_URL → параметры pg_dump
2. `pg_dump` (с таймаутом 10 мин) → SQL-файл
3. Сжатие gzip
4. Загрузка на Яндекс Диск выбранной компании
5. Запись в `backup_history`
6. Ротация (по возрасту и кол-ву копий)

**API:**
- `POST /api/backups/run` — ручной запуск
- `GET /api/backups/history` — история
- `GET /api/backups/status` — последний статус
- `DELETE /api/backups/{id}` — удаление

**Планировщик**: `app/core/scheduler.py` (APScheduler AsyncIOScheduler) вызывает `BackupService.run_backup()` по cron.

### SettingsService

**Файл**: `app/services/settings_service.py`

CRUD настроек из таблицы `system_settings`. Категории: `general`, `security`, `ar`, `storage`, `backup`.

**Методы:**
- `get_all_settings()` → `AllSettings` (все категории)
- `update_backup_settings(data: BackupSettings)` → сохранение настроек бэкапа
- `get_setting(key)` / `set_setting(key, value, type)` — единичные настройки

### VideoScheduler

**Файл**: `app/services/video_scheduler.py`

Логика выбора активного видео для AR-контента.

**Приоритеты:**
1. Видео с активным расписанием (`VideoRotationSchedule`)
2. Активное видео по `active_video_id`
3. Ротация (sequential / cyclic)
4. Fallback: любое активное видео

**Режимы:** `none` (фиксированное), `sequential` (1→2→3→stop), `cyclic` (1→2→3→1→...).

### ThumbnailService / EnhancedThumbnailService

**Файлы**: `app/services/thumbnail_service.py`, `enhanced_thumbnail_service.py`

Генерация превью:
- Фото → WebP, 3 размера (150×112, 320×240, 640×480)
- Видео → ffmpeg (извлечение кадра) → WebP, 3 размера
- Поддержка локального FS и Яндекс Диска

### ARCoreMarkerService

**Файл**: `app/services/marker_service.py`

Маркер для ARCore = загруженное фото. MindAR (.mind) не используется.
- `generate_marker()` → URL и путь фото
- `analyze_image_quality()` → оценка качества для трекинга

### NotificationService

**Файл**: `app/services/notification_service.py`

Создание уведомлений при событиях (создание AR-контента, изменение статуса и т.д.).

## Взаимодействие при создании AR-контента

```
POST /api/companies/{id}/projects/{id}/ar-content
    ↓
1. Валидация данных (Pydantic)
    ↓
2. Загрузка файлов (Storage Provider: local или YD)
    ↓
3. Генерация превью (ThumbnailService → WebP)
    ↓
4. Сохранение маркера (ARCoreMarkerService)
    ↓
5. Создание уведомления (NotificationService)
```

## Добавление нового сервиса

```python
# app/services/my_service.py
import structlog

logger = structlog.get_logger()

class MyService:
    """Описание сервиса."""

    async def do_something(self, param: str) -> dict:
        """Выполняет операцию."""
        logger.info("operation_started", param=param)
        try:
            result = await self._process(param)
            logger.info("operation_completed", result=result)
            return result
        except Exception as exc:
            logger.error("operation_failed", error=str(exc))
            raise
```

Далее — использовать через `Depends()` или прямой импорт в маршрутах.
