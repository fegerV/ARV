@echo off
chcp 65001 >nul
echo ========================================
echo Быстрый запуск Vertex AR
echo ========================================
echo.

echo [1/4] Создание директорий...
if not exist "tmp" mkdir tmp
if not exist "tmp\storage" mkdir tmp\storage
if not exist "tmp\storage\content" mkdir tmp\storage\content
if not exist "tmp\storage\thumbnails" mkdir tmp\storage\thumbnails
if not exist "tmp\storage\companies" mkdir tmp\storage\companies
echo OK: Директории созданы
echo.

echo [2/4] Настройка переменных окружения...
set DATABASE_URL=sqlite+aiosqlite:///./test_vertex_ar.db
set ADMIN_EMAIL=admin@vertexar.com
set ADMIN_DEFAULT_PASSWORD=admin123
set DEBUG=true
set ENVIRONMENT=development
set MEDIA_ROOT=./tmp/storage
set STORAGE_BASE_PATH=./tmp/storage
set LOCAL_STORAGE_PATH=./tmp/storage
set LOCAL_STORAGE_PUBLIC_URL=http://localhost:8000/storage
set PUBLIC_URL=http://localhost:8000
set LOG_LEVEL=INFO
echo OK: Переменные настроены
echo.

echo [3/4] Применение миграций...
alembic upgrade head
echo OK: Миграции применены
echo.

echo [4/4] Создание тестовых данных...
python scripts\legacy\create_test_data.py
echo.

echo ========================================
echo 🚀 ЗАПУСК СЕРВЕРА
echo ========================================
echo.
echo Сервер запускается на http://localhost:8000
echo Админ-панель: http://localhost:8000/admin
echo API документация: http://localhost:8000/docs
echo.
echo Для остановки сервера нажмите Ctrl+C
echo ========================================
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload