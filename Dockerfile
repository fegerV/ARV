FROM python:3.11-slim

# Установка переменных окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

# Создаем непривилегированного пользователя
RUN useradd -m -u 1000 appuser

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    postgresql-client \
    curl \
    ffmpeg \
    libffi-dev \
    libssl-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Node.js больше не требуется - используем HTML + Jinja2 + htmx + Alpine.js
# Все зависимости подгружаются через CDN, нет необходимости в сборке

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем gunicorn для использования в docker-compose
RUN pip install gunicorn

# Копируем исходный код приложения
COPY . .

# Node.js зависимости больше не требуются

# Создаем директории для хранения файлов
RUN mkdir -p /app/storage/content \
    /app/storage/thumbnails \
    /app/storage/markers \
    /app/storage/videos \
    /app/storage/temp \
    && chown -R appuser:appuser /app/storage

# Делаем entrypoint.sh исполняемым и копируем его
COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

# Переключаемся на непривилегированного пользователя
USER appuser

# Открываем порт
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health/status || exit 1

# Используем наш entrypoint script
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Default command for production
CMD ["gunicorn", "app.main:app", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--keep-alive", "5", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50", \
     "--access-logfile", "-"]