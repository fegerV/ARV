# MindAR Generator

Документация по генератору AR-маркеров на основе библиотеки MindAR.

## Обзор

MindAR Generator - это сервис для генерации `.mind` файлов (AR-маркеров) из изображений. Маркеры используются для распознавания изображений в AR-приложениях.

## Архитектура

### Компоненты

1. **MindARGenerator** (`app/services/mindar_generator.py`) - Основной Python сервис
2. **mindar_compiler.mjs** (`app/services/mindar_compiler.mjs`) - Node.js скрипт для компиляции
3. **MindARMarkerService** (`app/services/marker_service.py`) - Сервис для работы с маркерами

### Зависимости

#### Node.js

```json
{
  "dependencies": {
    "mind-ar": "^1.2.5",
    "canvas": "^3.2.0"
  }
}
```

Установка:
```bash
npm install
```

#### Python

Все зависимости включены в `requirements.txt`, дополнительные не требуются.

## Использование

### Базовое использование

```python
from app.services.mindar_generator import mindar_generator
from pathlib import Path

result = await mindar_generator.generate_and_upload_marker(
    ar_content_id="123",
    image_path=Path("/path/to/image.jpg"),
    max_features=1000,
    storage_path=Path("/storage/path")
)

if result["success"]:
    print(f"Маркер создан: {result['marker_path']}")
    print(f"Количество features: {result['features']}")
    print(f"Валидность: {result['is_valid']}")
```

### Через API

Маркеры автоматически генерируются при создании AR-контента через API:

```bash
POST /api/ar-content/
Content-Type: multipart/form-data

{
  "photo": <file>,
  "video": <file>,
  "company_id": 1,
  "project_id": 1,
  ...
}
```

## Процесс генерации

### 1. Подготовка изображения

- Проверка существования файла
- Валидация размера файла
- Разрешение относительных путей

### 2. Компиляция через Node.js

Скрипт `mindar_compiler.mjs`:
- Загружает изображение через `canvas`
- Использует `OfflineCompiler` из MindAR
- Извлекает features и descriptors
- Сохраняет в формате `.mind`

### 3. Валидация маркера

Проверяется:
- Структура JSON файла
- Наличие обязательных полей (`version`, `type`, `trackingData`)
- Количество features (должно быть > 0)
- Соответствие количества descriptors количеству features
- Размеры изображения

### 4. Fallback режим

Если компиляция не удалась, создается fallback маркер:
- Сохраняет размеры изображения
- Не содержит features (не будет работать для AR)
- Позволяет системе продолжить работу

## Конфигурация

### Настройки в config.py

```python
MINDAR_MAX_FEATURES: int = 1000  # Максимальное количество features
```

### Переменные окружения

Нет специальных переменных, используются стандартные настройки проекта.

## Формат .mind файла

```json
{
  "version": 2,
  "type": "image",
  "width": 1920,
  "height": 1080,
  "trackingData": {
    "features": [...],      // Массив features для распознавания
    "descriptors": [...],   // Дескрипторы features
    "imageSize": [1920, 1080]
  }
}
```

## Валидация маркеров

### Критерии валидности

- **Минимум features**: > 0 (обязательно)
- **Рекомендуемое количество**: > 50 для надежного трекинга
- **Предупреждения**:
  - < 10 features: очень ненадежный трекинг
  - < 50 features: качество трекинга может быть снижено
  - Descriptors не соответствуют features: возможны проблемы

### Статусы маркера

- `ready`: Маркер валиден и готов к использованию
- `ready_with_warnings`: Маркер создан, но есть предупреждения
- `ready_invalid`: Маркер создан, но не содержит features (fallback)

## Требования к изображениям

### Рекомендации

1. **Контрастность**: Высокая контрастность улучшает распознавание
2. **Резкость**: Четкие границы и детали
3. **Размер**: Минимум 640x480, рекомендуется 1920x1080 или выше
4. **Формат**: JPEG, PNG
5. **Содержимое**: Изображения с уникальными деталями работают лучше

### Плохие изображения для маркеров

- Однотонные изображения
- Размытые фотографии
- Изображения с низким контрастом
- Слишком простые паттерны

## Обработка ошибок

### Типичные ошибки

#### 1. MindAR dependencies not found

**Причина**: Не установлены Node.js зависимости

**Решение**:
```bash
npm install mind-ar canvas
```

#### 2. Input image not found

**Причина**: Неверный путь к изображению

**Решение**: Проверьте путь, используйте абсолютные пути или правильные относительные

#### 3. Compilation failed

**Причина**: Ошибка при компиляции через Node.js

**Решение**:
- Проверьте логи в `stderr`
- Убедитесь, что изображение валидно
- Попробуйте другое изображение

#### 4. Marker has no features

**Причина**: Изображение не подходит для генерации маркера

**Решение**:
- Используйте изображение с большим количеством деталей
- Увеличьте контрастность
- Попробуйте другое изображение

## Производительность

### Время генерации

- **Небольшие изображения** (< 1MB): 5-15 секунд
- **Средние изображения** (1-5MB): 15-30 секунд
- **Большие изображения** (> 5MB): 30-60 секунд

### Оптимизация

1. **max_features**: Уменьшение значения ускоряет генерацию, но снижает качество
2. **Размер изображения**: Предварительное масштабирование больших изображений
3. **Асинхронность**: Генерация выполняется асинхронно, не блокируя основной поток

## Интеграция с AR Viewer

Сгенерированные маркеры используются в AR viewer:

```html
<script src="https://cdn.jsdelivr.net/npm/mind-ar@1.2.5/dist/mindar-image.prod.js"></script>

<script>
  const mindarThree = new MindARThree.MindARThree({
    container: document.body,
    imageTargetSrc: '/path/to/marker.mind'
  });
</script>
```

## Логирование

Сервис использует `structlog` для логирования:

```python
logger.info("mindar_marker_generation_started", ...)
logger.info("mindar_marker_generation_success", ...)
logger.error("mindar_generation_error", ...)
logger.warning("marker_validation_failed", ...)
```

## Тестирование

### Ручное тестирование

```python
from app.services.mindar_generator import mindar_generator
from pathlib import Path

async def test_generation():
    result = await mindar_generator.generate_marker(
        image_path=Path("test_data/valid_test_image.png"),
        output_path=Path("test_output.mind"),
        max_features=1000
    )
    print(result)
```

### Проверка валидности

```python
from app.services.mindar_generator import mindar_generator

validation = mindar_generator.validate_marker_file(
    Path("marker.mind")
)
print(f"Valid: {validation['is_valid']}")
print(f"Features: {validation['features_count']}")
print(f"Warnings: {validation['warnings']}")
```

## Troubleshooting

### Проблема: Node.js не найден

**Решение**: Убедитесь, что Node.js установлен и доступен в PATH:
```bash
node --version
```

### Проблема: Canvas не работает

**Решение**: Установите системные зависимости для canvas:
```bash
# Ubuntu/Debian
sudo apt-get install build-essential libcairo2-dev libpango1.0-dev libjpeg-dev libgif-dev librsvg2-dev

# macOS
brew install pkg-config cairo pango libpng jpeg giflib librsvg
```

### Проблема: Маркеры не работают в AR viewer

**Решение**:
1. Проверьте валидность маркера
2. Убедитесь, что features > 0
3. Проверьте, что маркер загружается правильно
4. Используйте изображение с хорошим контрастом

## Дополнительные ресурсы

- [MindAR Documentation](https://github.com/hiukim/mind-ar-js)
- [MindAR Image Tracking](https://hiukim.github.io/mind-ar-js-doc/tools/compile/)
