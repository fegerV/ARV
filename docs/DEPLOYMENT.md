# Развертывание Vertex AR

## Локальное развертывание для тестов

### Требования
- Python 3.11+
- Node.js 18+ (для генерации AR-маркеров)
- Docker & Docker Compose (опционально)
- Git

### Шаг 1: Клонирование репозитория
```bash
git clone <repository-url>
cd ARV
```

### Шаг 2: Виртуальное окружение
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows
```

### Шаг 3: Зависимости
```bash
pip install -r requirements.txt
```

### Шаг 4: Настройка .env
```bash
DATABASE_URL=sqlite+aiosqlite:///./test_vertex_ar.db
SECRET_KEY=your-secret-key-here
LOG_LEVEL=INFO
STORAGE_BASE_PATH=./storage
LOCAL_STORAGE_PATH=./storage
```

### Шаг 5: Создание тестовых данных
```bash
python scripts/test_data/create_sample_data.py
```

### Шаг 6: Запуск сервера
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# или через скрипт
python scripts/servers/run_admin_test_server.py
```

### Шаг 7: Проверка
- Админ-панель: http://localhost:8000/admin
- API документация: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Продуктивное развертывание (Docker Compose)

### Шаг 1: .env для продакшена
```bash
cp .env.example .env.production
```

Настройте следующие переменные:
```bash
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql://user:password@db:5432/vertex_ar
SECRET_KEY=your-secure-secret-key-here
STORAGE_BASE_PATH=/app/storage
```

### Шаг 2: Запуск
```bash
docker compose up -d --build
```

## Проверка функциональности

### Проверка API
```bash
curl http://localhost:8000/health
```

### Проверка админки
- http://localhost:8000/admin

### Скрипты проверок
```bash
python scripts/checks/final_admin_check.py
python scripts/checks/check_ar_content_pages.py
```

## Troubleshooting

### Проблемы с БД
```bash
ls -la test_vertex_ar.db
alembic upgrade head
```

### Проблемы с MindAR
```bash
node -v
npm list mind-ar
npm list canvas
```

### Логи
```bash
tail -f logs/app.log
docker compose logs -f app
```

## Структура хранения файлов

### Новая структура (текущая)
```
storage/
└── VertexAR/
    └── {project_name}/
        └── {order_number}/
            ├── photo.{ext}
            ├── video.{ext}
            ├── qr_code.png
            ├── thumbnail.webp
            └── marker.mind
```

### Настройка STORAGE_BASE_PATH

В `.env` файле или переменных окружения:
```bash
STORAGE_BASE_PATH=./storage  # Относительно корня проекта
# или
STORAGE_BASE_PATH=/app/storage  # Абсолютный путь в контейнере
```

**Важно**: Убедитесь, что путь не содержит `/content/` в новой версии системы.
