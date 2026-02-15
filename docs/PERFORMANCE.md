# Оптимизация производительности

Руководство по оптимизации производительности платформы ARV.

## Обзор

Этот документ описывает стратегии оптимизации производительности, реализованные в платформе, и рекомендации по дальнейшему улучшению.

## Текущие оптимизации

### 1. Асинхронность

**Реализация:**
- FastAPI (асинхронный по умолчанию)
- SQLAlchemy async
- asyncpg для PostgreSQL
- Асинхронные сервисы

**Преимущества:**
- Параллельная обработка запросов
- Эффективное использование ресурсов
- Высокая пропускная способность

**Рекомендации:**
```python
# Всегда используйте async/await для I/O операций
async def get_ar_content(db: AsyncSession, content_id: int):
    result = await db.execute(select(ARContent).where(ARContent.id == content_id))
    return result.scalar_one_or_none()
```

### 2. Кэширование

**Многоуровневое кэширование:**

1. **L1 - In-Memory Cache** (EnhancedCacheService)
   - Быстрый доступ
   - Ограниченный размер (100MB)
   - LRU eviction

2. **L2 - Redis Cache** (планируется)
   - Распределенное кэширование
   - Персистентность
   - TTL управление

3. **L3 - Disk Cache**
   - Долгосрочное хранение
   - Сжатие данных
   - Большой объем

**Использование:**
```python
from app.services.enhanced_cache_service import EnhancedCacheService

cache = EnhancedCacheService()

# Получить из кэша
value = await cache.get("key", cache_type="metadata")

# Сохранить в кэш
await cache.set("key", value, cache_type="metadata", ttl=3600)
```

**Рекомендации:**

1. **Кэшируйте часто запрашиваемые данные:**
   - Метаданные AR-контента
   - Списки проектов и компаний
   - Настройки системы

2. **Используйте правильные TTL:**
   ```python
   # Статические данные - долгий TTL
   await cache.set("companies", companies, ttl=86400)  # 24 часа
   
   # Динамические данные - короткий TTL
   await cache.set("active_users", count, ttl=60)  # 1 минута
   ```

3. **Инвалидация кэша:**
   ```python
   # При обновлении данных
   await cache.delete("companies")
   await cache.set("companies", updated_companies)
   ```

### 3. Оптимизация запросов к БД

**Рекомендации:**

1. **Используйте selectinload для связей:**
   ```python
   from sqlalchemy.orm import selectinload
   
   stmt = select(ARContent).options(
       selectinload(ARContent.project),
       selectinload(ARContent.company),
       selectinload(ARContent.videos)
   )
   ```

2. **Используйте индексы:**
   - Все внешние ключи индексированы
   - Часто запрашиваемые поля индексированы
   - Составные индексы для сложных запросов

3. **Избегайте N+1 запросов:**
   ```python
   # ПЛОХО - N+1 запросов
   for content in ar_contents:
       project = await db.get(Project, content.project_id)
   
   # ХОРОШО - один запрос
   stmt = select(ARContent).options(selectinload(ARContent.project))
   ```

4. **Используйте пагинацию:**
   ```python
   stmt = select(ARContent).limit(20).offset(page * 20)
   ```

### 4. Сжатие ответов

**Реализация:**
- GZip middleware для ответов > 500 байт

**Рекомендации:**
```python
# В main.py уже настроено
app.add_middleware(
    GZipMiddleware,
    minimum_size=500,
)
```

### 5. Connection Pooling

**Реализация:**
- SQLAlchemy connection pool
- Настройки в config.py

**Рекомендации:**
```python
# Для продакшена
DB_POOL_SIZE = 20
DB_MAX_OVERFLOW = 10
DB_POOL_PRE_PING = True  # Проверка соединений
```

## Оптимизация генерации маркеров

### Текущая реализация

- Маркер = загруженное фото (без отдельной генерации)
- Timeout 5 минут
- Валидация маркеров

### Рекомендации

1. **Кэшируйте результаты генерации:**
   ```python
   # Если маркер уже сгенерирован, не генерируйте заново
   if await cache.get(f"marker_{ar_content_id}"):
       return cached_marker
   ```

2. **Используйте фоновые задачи:**
   ```python
   from fastapi import BackgroundTasks
   
   @router.post("/api/ar-content/")
   async def create_ar_content(
       background_tasks: BackgroundTasks,
       ...
   ):
       # Создать контент
       ar_content = await create_content(...)
       
       # Генерация маркера в фоне
       background_tasks.add_task(generate_marker, ar_content.id)
   ```

3. **Оптимизируйте параметры генерации:**
   ```python
   # Уменьшите max_features для быстрой генерации
   MINDAR_MAX_FEATURES = 500  # Вместо 1000
   ```

## Оптимизация работы с файлами

### Рекомендации

1. **Используйте асинхронную работу с файлами:**
   ```python
   import aiofiles
   
   async with aiofiles.open(file_path, 'rb') as f:
       content = await f.read()
   ```

2. **Оптимизируйте генерацию превью:**
   - Генерируйте превью асинхронно
   - Кэшируйте превью
   - Используйте WebP формат

3. **Используйте CDN для статических файлов:**
   - CloudFlare
   - AWS CloudFront
   - Yandex CDN

## Мониторинг производительности

### Метрики Prometheus

**Реализовано:**
- Cache operations
- Circuit breaker state
- Operation duration
- Health check status

**Использование:**
```python
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)
```

### Логирование производительности

**Рекомендации:**
```python
import time
import structlog

logger = structlog.get_logger()

async def slow_operation():
    start_time = time.time()
    # ... операция ...
    duration = time.time() - start_time
    
    logger.info(
        "operation_completed",
        operation="slow_operation",
        duration_seconds=duration,
        duration_ms=duration * 1000
    )
```

## Оптимизация базы данных

### Индексы

**Текущие индексы:**
- `users.email` - уникальный
- `companies.slug` - уникальный
- `projects.company_id` - для фильтрации
- `ar_content.project_id` - для фильтрации
- `ar_content.unique_id` - для публичных ссылок
- `ar_content.status` - для фильтрации

**Рекомендации:**

1. **Добавьте индексы для часто используемых запросов:**
   ```sql
   CREATE INDEX idx_ar_content_created_at ON ar_content(created_at DESC);
   CREATE INDEX idx_videos_ar_content_status ON videos(ar_content_id, status);
   ```

2. **Используйте составные индексы:**
   ```sql
   CREATE INDEX idx_ar_content_company_project 
   ON ar_content(company_id, project_id, status);
   ```

### Оптимизация запросов

1. **Используйте EXPLAIN для анализа:**
   ```sql
   EXPLAIN ANALYZE SELECT * FROM ar_content WHERE project_id = 1;
   ```

2. **Избегайте SELECT *:**
   ```python
   # ПЛОХО
   stmt = select(ARContent)
   
   # ХОРОШО
   stmt = select(ARContent.id, ARContent.order_number, ARContent.status)
   ```

3. **Используйте агрегатные функции:**
   ```python
   from sqlalchemy import func
   
   stmt = select(func.count(ARContent.id)).where(ARContent.project_id == project_id)
   ```

## Оптимизация фронтенда

### Минимизация JavaScript

**Текущая реализация:**
- htmx + Alpine.js (минимальный JS)
- Загрузка через CDN

**Рекомендации:**

1. **Используйте минифицированные версии:**
   ```html
   <script src="https://cdn.jsdelivr.net/npm/htmx.org@1.9.10/dist/htmx.min.js"></script>
   ```

2. **Отложенная загрузка:**
   ```html
   <script defer src="alpine.js"></script>
   ```

### Оптимизация изображений

1. **Используйте WebP формат:**
   - Меньший размер
   - Лучшее качество
   - Поддержка в современных браузерах

2. **Ленивая загрузка:**
   ```html
   <img loading="lazy" src="image.jpg" alt="...">
   ```

3. **Responsive images:**
   ```html
   <img srcset="small.jpg 480w, large.jpg 1920w" 
        sizes="(max-width: 600px) 480px, 1920px"
        src="large.jpg">
   ```

## Масштабирование

### Горизонтальное масштабирование

**Рекомендации:**

1. **Stateless приложение:**
   - JWT токены (stateless)
   - Нет сессий на сервере
   - Общее хранилище файлов

2. **Load balancing:**
   ```nginx
   upstream app_servers {
       least_conn;
       server app1:8000;
       server app2:8000;
       server app3:8000;
   }
   ```

3. **Распределенное кэширование:**
   - Redis для кэша
   - Синхронизация между инстансами

### Вертикальное масштабирование

**Рекомендации:**

1. **Оптимизация памяти:**
   - Увеличение размера connection pool
   - Оптимизация кэша
   - Мониторинг использования памяти

2. **Оптимизация CPU:**
   - Асинхронная обработка
   - Фоновые задачи
   - Параллельная обработка

## Best Practices

### 1. Профилирование

```python
import cProfile
import pstats

def profile_function(func):
    profiler = cProfile.Profile()
    profiler.enable()
    result = func()
    profiler.disable()
    
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)
    
    return result
```

### 2. Асинхронная обработка тяжелых операций

```python
from fastapi import BackgroundTasks

@router.post("/api/process/")
async def process_data(
    background_tasks: BackgroundTasks,
    data: Data
):
    # Быстрый ответ
    task_id = generate_task_id()
    
    # Тяжелая обработка в фоне
    background_tasks.add_task(heavy_processing, task_id, data)
    
    return {"task_id": task_id, "status": "processing"}
```

### 3. Batch операции

```python
# ПЛОХО - множественные запросы
for item in items:
    await db.add(item)
    await db.commit()

# ХОРОШО - один запрос
for item in items:
    db.add(item)
await db.commit()
```

### 4. Использование индексов

```python
# Всегда используйте индексированные поля для фильтрации
stmt = select(ARContent).where(
    ARContent.project_id == project_id,  # Индексировано
    ARContent.status == "active"  # Индексировано
)
```

## Метрики для мониторинга

### Ключевые метрики

1. **Response Time:**
   - Среднее время ответа
   - P95, P99 перцентили
   - Медленные запросы

2. **Throughput:**
   - Запросов в секунду
   - Обработанных операций

3. **Error Rate:**
   - Процент ошибок
   - Типы ошибок

4. **Resource Usage:**
   - CPU использование
   - Память
   - Диск I/O
   - Сетевой трафик

5. **Database:**
   - Время выполнения запросов
   - Количество соединений
   - Размер БД

## Инструменты

### Профилирование

- **cProfile** - встроенный профилировщик Python
- **py-spy** - sampling profiler
- **memory_profiler** - профилирование памяти

### Мониторинг

- **Prometheus** - сбор метрик
- **Grafana** - визуализация
- **Sentry** - отслеживание ошибок
- **New Relic** - APM (Application Performance Monitoring)

### Тестирование нагрузки

- **Locust** - нагрузочное тестирование
- **Apache Bench (ab)** - простой тест нагрузки
- **wrk** - современный инструмент для нагрузочного тестирования

## Дополнительные ресурсы

- [FastAPI Performance](https://fastapi.tiangolo.com/advanced/performance/)
- [SQLAlchemy Performance](https://docs.sqlalchemy.org/en/20/faq/performance.html)
- [Python Performance Tips](https://wiki.python.org/moin/PythonSpeed/PerformanceTips)
