# Структура репозитория ARV

Репозиторий организован как **монорепо**: бэкенд и веб-админка в одной кодовой базе, мобильное приложение AR Viewer — в подкаталоге.

## Основные части

| Каталог | Назначение |
|---------|------------|
| **app/** | Backend: FastAPI-приложение (API, HTML-маршруты, сервисы, модели, конфигурация). |
| **android/** | AR Viewer — Android-приложение (ARCore + Kotlin) для просмотра AR по маркеру. |
| **templates/** | HTML-шаблоны (Jinja2) для админки и лендинга `/view/{unique_id}`. |
| **static/** | CSS, JS, статика для веб-интерфейса. |
| **alembic/** | Миграции БД. |
| **docs/** | Документация (API, архитектура, troubleshooting и т.д.). |
| **tests/** | Тесты бэкенда (pytest). |
| **scripts/** | Вспомогательные скрипты (проверки, тестовые данные, серверы). |

## Backend (app/)

- **api/routes/** — REST API (auth, companies, projects, ar_content, viewer, videos, storage, notifications и др.).
- **html/routes/** — серверный рендеринг страниц админки.
- **core/** — config, database, security.
- **models/** — SQLAlchemy-модели.
- **schemas/** — Pydantic-схемы.
- **services/** — бизнес-логика (video_scheduler, marker_service, notification_service и т.д.).

Подробнее: [ARCHITECTURE.md](ARCHITECTURE.md).

## AR Viewer (android/)

В каталоге `android/` размещается проект приложения для Android (Kotlin, ARCore). Оно использует Viewer API бэкенда (манифест, `/check`, active-video) и открывается по ссылке `https://your-domain.com/view/{unique_id}` (App Links) или по схеме `arv://view/{unique_id}`.

Контракт API и рекомендации по совместимости при изменениях бэкенда описаны в [API.md](API.md#viewer-api-contract-android).

## CI

- **Backend:** тесты и линты (pytest, ruff) — см. `.github/workflows/backend.yml`.
- **Android:** сборка приложения из `android/` (Gradle) при изменении файлов в `android/` — см. `.github/workflows/android.yml`.
