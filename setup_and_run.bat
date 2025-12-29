@echo off
chcp 65001 >nul
echo ========================================
echo Настройка окружения Vertex AR
echo ========================================
echo.

echo [1/5] Установка зависимостей Python...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ОШИБКА: Не удалось установить зависимости
    pause
    exit /b 1
)
echo OK: Зависимости установлены
echo.

echo [2/5] Создание директории для хранения...
if not exist "tmp\storage" mkdir tmp\storage
if not exist "tmp\storage\content" mkdir tmp\storage\content
if not exist "tmp\storage\thumbnails" mkdir tmp\storage\thumbnails
echo OK: Директории созданы
echo.

echo [3/5] Настройка переменных окружения...
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
echo OK: Переменные окружения настроены
echo.

echo [4/5] Применение миграций базы данных...
alembic upgrade head
if %errorlevel% neq 0 (
    echo ОШИБКА: Не удалось применить миграции
    pause
    exit /b 1
)
echo OK: Миграции применены
echo.

echo [5/5] Запуск сервера...
echo.
echo ========================================
echo Сервер запускается на http://localhost:8000
echo Админ-панель: http://localhost:8000/admin
echo API документация: http://localhost:8000/docs
echo ========================================
echo.
echo Для остановки сервера нажмите Ctrl+C
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload