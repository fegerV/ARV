# 🚀 Thumbnail System - Quick Start Guide

Быстрый старт для системы генерации превью. 5 минут до запуска!

---

## ⚡ Шаг 1: Rebuild Docker (2 мин)

```bash
# Остановить контейнеры
docker-compose down

# Rebuild с новыми зависимостями (FFmpeg)
docker-compose build app celery-worker

# Запустить
docker-compose up -d
```

---

## 📊 Шаг 2: Применить миграцию (30 сек)

```bash
# Проверить текущую версию
docker-compose exec app alembic current

# Применить миграцию для thumbnail полей
docker-compose exec app alembic upgrade head

# Проверить успех
docker-compose exec app alembic current
# Должно быть: 20251205_thumbnails
```

---

## ✅ Шаг 3: Проверка FFmpeg (30 сек)

```bash
# Проверить установку FFmpeg
docker-compose exec app ffmpeg -version
# Должно вывести версию FFmpeg

# Проверить Python библиотеку
docker-compose exec app python -c "import ffmpeg; print('OK')"
# Должно вывести: OK
```

---

## 🧪 Шаг 4: Тестовая загрузка (1 мин)

### Создать AR контент с портретом

```bash
curl -X POST http://localhost:8000/api/ar-content \
  -F "company_id=1" \
  -F "project_id=1" \
  -F "title=Test Portrait" \
  -F "description=Test" \
  -F "image=@/path/to/portrait.jpg"
```

**Response**:
```json
{
  "id": 1,
  "unique_id": "550e8400...",
  "image_url": "/storage/ar_content/.../portrait.jpg",
  "marker_status": "pending",
  "marker_task_id": "abc-123",
  "thumbnail_task_id": "def-456"  ← НОВОЕ!
}
```

### Загрузить видео

```bash
curl -X POST http://localhost:8000/api/ar-content/1/videos \
  -F "file=@/path/to/video.mp4" \
  -F "title=Test Video" \
  -F "is_active=true"
```

**Response**:
```json
{
  "id": 1,
  "video_url": "/storage/.../video.mp4",
  "is_active": true,
  "thumbnail_task_id": "xyz-789"  ← НОВОЕ!
}
```

---

## 🔍 Шаг 5: Проверка работы (1 мин)

### Проверить логи Celery

```bash
# Смотреть логи в реальном времени
docker-compose logs -f celery-worker

# Должны быть строки:
# "Starting video thumbnail generation" video_id=1
# "Extracting frame from video" duration=...
# "Generated thumbnail" size=small url=...
# "Video thumbnails generated successfully"
```

### Проверить БД

```bash
docker-compose exec postgres psql -U vertex_ar -c \
  "SELECT id, title, thumbnail_url, thumbnail_small_url, thumbnail_large_url FROM videos WHERE id = 1;"
```

**Ожидаемый результат**:
```
 id |   title    |        thumbnail_url         |     thumbnail_small_url      |     thumbnail_large_url
----+------------+------------------------------+------------------------------+-----------------------------
  1 | Test Video | /storage/thumbnails/videos/... | /storage/thumbnails/videos/... | /storage/thumbnails/videos/...
```

### Проверить файлы в storage

```bash
# Локальное хранилище
ls -lh storage/thumbnails/videos/1/
# Должно быть 3 файла: *_small.webp, *_medium.webp, *_large.webp

ls -lh storage/thumbnails/portraits/1/
# Должно быть 3 файла для портрета
```

---

## 🎨 Frontend - Использование компонентов

### Установить в существующую страницу

**Файл**: `frontend/src/pages/ar-content/ARContentDetail.tsx`

```tsx
import { VideoPreview, ImagePreview } from '@/components';

// В компоненте:
<VideoPreview
  video={{
    id: 1,
    title: "Test Video",
    video_url: "/storage/video.mp4",
    thumbnail_url: "/storage/thumbnails/medium.webp",
    thumbnail_small_url: "/storage/thumbnails/small.webp",
    thumbnail_large_url: "/storage/thumbnails/large.webp",
    duration: 125,
    is_active: true
  }}
  size="medium"
  onClick={() => console.log('Play video')}
/>
```

### Build frontend

```bash
cd frontend
npm install  # если еще не делали
npm run build
```

---

## 🐛 Troubleshooting

### Проблема: "FFmpeg not found"

```bash
# Rebuild с чистого листа
docker-compose build --no-cache app celery-worker
```

### Проблема: "Celery task failed"

```bash
# Проверить детальные логи
docker-compose logs celery-worker | grep ERROR

# Проверить Redis
docker-compose exec redis redis-cli ping
# Должно ответить: PONG

# Restart celery
docker-compose restart celery-worker
```

### Проблема: "Thumbnails not appearing"

```bash
# Проверить права доступа
docker-compose exec app ls -la /app/storage/thumbnails/

# Если нет папки, создать:
docker-compose exec app mkdir -p /app/storage/thumbnails/videos
docker-compose exec app mkdir -p /app/storage/thumbnails/portraits
docker-compose exec app chown -R appuser:appuser /app/storage
```

### Проблема: "Migration already exists"

```bash
# Откатить миграцию
docker-compose exec app alembic downgrade -1

# Применить снова
docker-compose exec app alembic upgrade head
```

---

## 📊 Проверка производительности

### Замерить время генерации

```bash
# Запустить задачу вручную
docker-compose exec app python << EOF
import time
from app.tasks.thumbnail_generator import generate_video_thumbnail

start = time.time()
result = generate_video_thumbnail.delay(1)
thumbnails = result.get(timeout=120)
elapsed = time.time() - start

print(f"Thumbnails: {thumbnails}")
print(f"Time: {elapsed:.2f}s")
EOF
```

**Ожидаемое время**:
- Изображение: 2-3 сек
- Видео (30 сек): 5-7 сек
- Видео (2 мин): 10-15 сек

---

## ✅ Success Criteria

Система работает корректно, если:

- [x] FFmpeg установлен: `docker-compose exec app ffmpeg -version`
- [x] Миграция применена: `alembic current` → `20251205_thumbnails`
- [x] Celery worker запущен: `docker-compose ps celery-worker` → `Up`
- [x] Загрузка видео запускает задачу: логи содержат `"Starting video thumbnail generation"`
- [x] Превью генерируются: 3 WebP файла в `storage/thumbnails/videos/{id}/`
- [x] БД обновлена: поля `thumbnail_url`, `thumbnail_small_url`, `thumbnail_large_url` заполнены
- [x] Frontend компоненты импортируются: `import { VideoPreview } from '@/components'`

---

## 🎯 Next Steps

После успешного запуска:

1. **Интегрировать компоненты в UI**:
   - Добавить VideoPreview в страницу AR контента
   - Добавить ImagePreview в галерею портретов

2. **Настроить мониторинг**:
   - Добавить метрики Celery в Prometheus
   - Настроить alerts для failed tasks

3. **Оптимизировать**:
   - Настроить CDN для превью
   - Добавить lazy loading для списков

4. **Документация**:
   - Прочитать `THUMBNAIL_SYSTEM.md` для деталей
   - Изучить `THUMBNAIL_USAGE_EXAMPLES.md` для примеров

---

## 📚 Полезные ссылки

- **Архитектура**: [THUMBNAIL_SYSTEM.md](./THUMBNAIL_SYSTEM.md)
- **Примеры использования**: [THUMBNAIL_USAGE_EXAMPLES.md](./THUMBNAIL_USAGE_EXAMPLES.md)
- **Итоговый отчет**: [THUMBNAIL_IMPLEMENTATION_SUMMARY.md](./THUMBNAIL_IMPLEMENTATION_SUMMARY.md)

---

**Готово! Система превью работает! 🎉**

Если возникли проблемы, проверьте раздел Troubleshooting или откройте issue.
