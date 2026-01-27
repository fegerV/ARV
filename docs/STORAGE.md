# Система хранения файлов

Подробное описание системы хранения файлов в платформе ARV.

## Обзор

Платформа использует абстракцию провайдеров хранения для работы с файлами. В настоящее время поддерживается локальное файловое хранилище, с возможностью расширения до облачных провайдеров (S3, Yandex Object Storage).

## Архитектура хранения

### Абстракция провайдеров

Система использует паттерн Strategy для поддержки различных провайдеров хранения:

```python
StorageProvider (ABC)
    ↓
LocalStorageProvider
    ↓
S3StorageProvider (планируется)
    ↓
YandexStorageProvider (планируется)
```

### Основные компоненты

1. **StorageProvider** (`app/core/storage_providers.py`) - Абстрактный базовый класс
2. **LocalStorageProvider** - Реализация для локального хранилища
3. **get_storage_provider()** - Фабрика для получения провайдера

## Структура хранения

### Новая структура (текущая)

```
storage/
└── VertexAR/
    └── {project_name}/
        └── {order_number}/
            ├── photo.{ext}          # Фото заказчика
            ├── video.{ext}          # Видео (deprecated, используется videos/)
            ├── marker.mind          # AR-маркер
            ├── thumbnail.webp       # Превью фото
            └── qr_code.png         # QR-код для AR viewer
```

**Пример:**
```
storage/VertexAR/Портреты/ORD-20260125-4492/
├── photo.jpg
├── marker.mind
├── thumbnail.webp
└── qr_code.png
```

### Структура для видео

Видео хранятся отдельно в подпапке `videos/`:

```
storage/VertexAR/{project_name}/{order_number}/
└── videos/
    ├── video_1.mp4
    ├── video_1_thumbnail.webp
    ├── video_2.mp4
    └── video_2_thumbnail.webp
```

### Старая структура (поддерживается для обратной совместимости)

```
storage/content/VertexAR/Posters/{company_id}_{company_name}/{project_name}/{order_number}/
```

## Генерация путей

### Путь для AR-контента

Путь генерируется на основе:
- Названия проекта
- Номера заказа

**Формат:**
```
VertexAR/{project_name}/{order_number}/
```

**Пример кода:**
```python
from app.utils.ar_content import build_storage_path

storage_path = build_storage_path(
    project_name="Портреты",
    order_number="ORD-20260125-4492"
)
# Результат: VertexAR/Портреты/ORD-20260125-4492/
```

### Публичные URL

Публичные URL генерируются на основе пути хранения:

**Формат:**
```
/storage/{storage_path}
```

**Пример:**
```
/storage/VertexAR/Портреты/ORD-20260125-4492/photo.jpg
```

## Провайдеры хранения

### LocalStorageProvider

**Описание**: Локальное файловое хранилище на диске сервера

**Конфигурация:**
- `STORAGE_BASE_PATH` - Базовый путь для хранения (по умолчанию: `./storage`)
- `LOCAL_STORAGE_PUBLIC_URL` - Базовый URL для публичного доступа (по умолчанию: `http://localhost:8000/storage`)

**Особенности:**
- Файлы хранятся на локальной файловой системе
- Публичный доступ через FastAPI StaticFiles
- Поддержка Windows и Unix-систем
- Автоматическое создание директорий

**Использование:**
```python
from app.core.storage_providers import get_storage_provider

provider = get_storage_provider()
url = await provider.save_file(
    source_path="/tmp/upload.jpg",
    destination_path="VertexAR/Project/Order/photo.jpg"
)
```

### S3StorageProvider (планируется)

**Описание**: Хранилище в AWS S3

**Конфигурация:**
- `S3_BUCKET` - Имя S3 bucket
- `S3_REGION` - Регион S3
- `S3_ACCESS_KEY` - Access key
- `S3_SECRET_KEY` - Secret key

**Особенности:**
- Масштабируемое хранилище
- Высокая доступность
- CDN интеграция
- Версионирование файлов

### YandexStorageProvider (планируется)

**Описание**: Хранилище в Yandex Object Storage

**Конфигурация:**
- `YANDEX_BUCKET` - Имя bucket
- `YANDEX_ACCESS_KEY` - Access key
- `YANDEX_SECRET_KEY` - Secret key
- `YANDEX_ENDPOINT` - Endpoint URL

**Особенности:**
- S3-совместимый API
- Региональное хранение
- Низкая стоимость
- Интеграция с Yandex Cloud

## API провайдеров

### StorageProvider (абстрактный класс)

Все провайдеры должны реализовать следующие методы:

#### save_file()

```python
async def save_file(
    self, 
    source_path: str, 
    destination_path: str
) -> str:
    """
    Сохранить файл в хранилище.
    
    Args:
        source_path: Локальный путь к исходному файлу
        destination_path: Путь назначения в хранилище (относительный)
    
    Returns:
        Публичный URL файла
    """
```

#### get_file()

```python
async def get_file(
    self, 
    storage_path: str, 
    local_path: str
) -> bool:
    """
    Получить файл из хранилища.
    
    Args:
        storage_path: Путь в хранилище (относительный)
        local_path: Локальный путь для сохранения
    
    Returns:
        True если успешно, False иначе
    """
```

#### delete_file()

```python
async def delete_file(self, storage_path: str) -> bool:
    """
    Удалить файл из хранилища.
    
    Args:
        storage_path: Путь в хранилище (относительный)
    
    Returns:
        True если успешно, False иначе
    """
```

#### file_exists()

```python
async def file_exists(self, storage_path: str) -> bool:
    """
    Проверить существование файла.
    
    Args:
        storage_path: Путь в хранилище (относительный)
    
    Returns:
        True если файл существует, False иначе
    """
```

#### get_public_url()

```python
def get_public_url(self, storage_path: str) -> str:
    """
    Получить публичный URL файла.
    
    Args:
        storage_path: Путь в хранилище (относительный)
    
    Returns:
        Публичный URL
    """
```

#### get_usage_stats()

```python
async def get_usage_stats(self, path: str = "") -> Dict[str, Any]:
    """
    Получить статистику использования хранилища.
    
    Args:
        path: Путь для анализа (относительный, пустой для корня)
    
    Returns:
        Словарь со статистикой
    """
```

## Работа с файлами

### Сохранение файла

```python
from app.core.storage_providers import get_storage_provider
from pathlib import Path

# Получить провайдер
provider = get_storage_provider()

# Сохранить файл
public_url = await provider.save_file(
    source_path="/tmp/uploaded_photo.jpg",
    destination_path="VertexAR/Портреты/ORD-001/photo.jpg"
)

print(f"Файл доступен по адресу: {public_url}")
```

### Получение файла

```python
# Получить файл из хранилища
success = await provider.get_file(
    storage_path="VertexAR/Портреты/ORD-001/photo.jpg",
    local_path="/tmp/downloaded_photo.jpg"
)

if success:
    print("Файл успешно загружен")
```

### Проверка существования

```python
# Проверить существование файла
exists = await provider.file_exists(
    "VertexAR/Портреты/ORD-001/photo.jpg"
)

if exists:
    print("Файл существует")
```

### Получение публичного URL

```python
# Получить публичный URL
url = provider.get_public_url(
    "VertexAR/Портреты/ORD-001/photo.jpg"
)
# Результат: /storage/VertexAR/Портреты/ORD-001/photo.jpg
```

### Удаление файла

```python
# Удалить файл
success = await provider.delete_file(
    "VertexAR/Портреты/ORD-001/photo.jpg"
)

if success:
    print("Файл удален")
```

### Статистика использования

```python
# Получить статистику
stats = await provider.get_usage_stats("VertexAR/Портреты")

print(f"Всего файлов: {stats['total_files']}")
print(f"Общий размер: {stats['total_size_mb']} MB")
```

## Типы файлов

### Фото заказчика

- **Формат**: JPEG, PNG
- **Максимальный размер**: 10 MB
- **Путь**: `{order_path}/photo.{ext}`
- **Использование**: Распознавание в AR viewer

### Видео

- **Формат**: MP4, WebM, MOV
- **Максимальный размер**: 100 MB
- **Путь**: `{order_path}/videos/video_{id}.{ext}`
- **Использование**: Воспроизведение в AR viewer

### AR-маркеры

- **Формат**: .mind (JSON)
- **Путь**: `{order_path}/marker.mind`
- **Использование**: Распознавание изображений в MindAR
- **Генерация**: Автоматически через MindAR Generator

### Превью (thumbnails)

- **Формат**: WebP
- **Путь**: `{order_path}/thumbnail.webp` (для фото)
- **Путь**: `{order_path}/videos/video_{id}_thumbnail.webp` (для видео)
- **Использование**: Быстрая загрузка в списках
- **Генерация**: Автоматически при загрузке

### QR-коды

- **Формат**: PNG
- **Путь**: `{order_path}/qr_code.png`
- **Использование**: Быстрый доступ к AR viewer
- **Генерация**: Автоматически при создании AR-контента

## Конфигурация

### Переменные окружения

```bash
# Базовый путь для хранения
STORAGE_BASE_PATH=./storage

# Локальное хранилище
LOCAL_STORAGE_PATH=./storage
LOCAL_STORAGE_PUBLIC_URL=http://localhost:8000/storage

# Публичный URL приложения
PUBLIC_URL=http://localhost:8000
```

### Настройки в config.py

```python
# Storage
STORAGE_BASE_PATH: str = "./storage"

# Local Storage
LOCAL_STORAGE_PATH: str = "./storage"
LOCAL_STORAGE_PUBLIC_URL: str = "http://localhost:8000/storage"

# File storage configuration
ALLOWED_FILE_EXTENSIONS_PHOTO: list[str] = ["jpeg", "jpg", "png"]
ALLOWED_FILE_EXTENSIONS_VIDEO: list[str] = ["mp4", "webm", "mov"]
MAX_FILE_SIZE_PHOTO: int = 10 * 1024 * 1024  # 10MB
MAX_FILE_SIZE_VIDEO: int = 100 * 1024 * 1024  # 100MB
```

## Публичный доступ

### FastAPI StaticFiles

Файлы доступны публично через FastAPI StaticFiles:

```python
# В main.py
app.mount("/storage", StaticFiles(directory=storage_dir), name="storage")
```

**Доступ:**
```
http://localhost:8000/storage/VertexAR/Портреты/ORD-001/photo.jpg
```

### Безопасность

- Файлы доступны публично по дизайну (для AR viewer)
- Нет аутентификации для статических файлов
- Используйте уникальные `unique_id` для AR-контента
- Не храните чувствительные данные в публичных файлах

## Миграция между провайдерами

### План миграции

1. **Подготовка**: Настроить новый провайдер
2. **Копирование**: Скопировать все файлы в новое хранилище
3. **Обновление URL**: Обновить URL в базе данных
4. **Тестирование**: Проверить доступность файлов
5. **Переключение**: Изменить активный провайдер
6. **Очистка**: Удалить старые файлы (опционально)

### Пример миграции

```python
from app.core.storage_providers import get_storage_provider
from app.models import ARContent

async def migrate_to_s3(db: AsyncSession):
    old_provider = LocalStorageProvider()
    new_provider = S3StorageProvider()
    
    # Получить весь AR-контент
    ar_contents = await db.execute(select(ARContent))
    
    for content in ar_contents.scalars():
        # Копировать файлы
        if content.photo_path:
            await new_provider.save_file(
                source_path=old_provider._get_full_path(content.photo_path),
                destination_path=content.photo_path
            )
        
        # Обновить URL
        content.photo_url = new_provider.get_public_url(content.photo_path)
        await db.commit()
```

## Резервное копирование

### Автоматическое резервное копирование

Система поддерживает автоматическое резервное копирование в S3:

**Конфигурация:**
```bash
BACKUP_S3_ENDPOINT=https://s3.amazonaws.com
BACKUP_S3_ACCESS_KEY=your-access-key
BACKUP_S3_SECRET_KEY=your-secret-key
BACKUP_S3_BUCKET=vertex-ar-backups
BACKUP_RETENTION_DAYS=30
```

**Скрипты:**
- `scripts/backup/continuous-backup.sh` - Непрерывное резервное копирование
- `scripts/backup/backup-test.sh` - Тестирование резервного копирования

## Мониторинг

### Статистика использования

```python
# Получить статистику для всего хранилища
stats = await provider.get_usage_stats()

print(f"Всего файлов: {stats['total_files']}")
print(f"Общий размер: {stats['total_size_mb']} MB")
```

### Проверка доступности

```python
# Проверить доступность хранилища
try:
    test_path = "test_file.txt"
    await provider.save_file("/tmp/test.txt", test_path)
    exists = await provider.file_exists(test_path)
    await provider.delete_file(test_path)
    print("Хранилище работает корректно")
except Exception as e:
    print(f"Ошибка хранилища: {e}")
```

## Best Practices

1. **Используйте относительные пути** для destination_path
2. **Проверяйте существование файлов** перед операциями
3. **Обрабатывайте ошибки** при работе с файлами
4. **Логируйте операции** с файлами
5. **Используйте транзакции** при обновлении БД и файлов
6. **Регулярно делайте резервные копии**
7. **Мониторьте использование диска**
8. **Очищайте неиспользуемые файлы**

## Troubleshooting

### Проблема: Файлы не сохраняются

**Решение:**
1. Проверьте права доступа к директории
2. Проверьте свободное место на диске
3. Проверьте путь в STORAGE_BASE_PATH

### Проблема: Файлы не доступны публично

**Решение:**
1. Проверьте, что StaticFiles смонтирован в main.py
2. Проверьте PUBLIC_URL в настройках
3. Проверьте путь к файлу в БД

### Проблема: Недостаточно места

**Решение:**
1. Очистите старые файлы
2. Настройте автоматическую очистку
3. Рассмотрите миграцию на облачное хранилище

## Дополнительные ресурсы

- [FastAPI StaticFiles](https://fastapi.tiangolo.com/tutorial/static-files/)
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [Yandex Object Storage](https://cloud.yandex.ru/docs/storage/)
