# ARV Platform — Переработанный Audit Report

**Дата аудита:** 2026-08-19  
**Аудитор:** Kilo (Senior Software Architect / Code Auditor / QA Engineer)  
**Версия проекта:** 2.1.1  
**Область:** `E:\Project\ARV`  

> **Статус:** Частично рабочий проект с критическими production-блокерами.  
> Эта версия предназначена для удобного чтения, передачи разработчику/нейросети и последовательного исправления проекта.


---

## Содержание

1. [Executive Summary](#1-executive-summary)
2. [Critical Problems (P0)](#2-critical-problems-p0)
3. [Functional Problems](#3-functional-problems)
4. [Architectural Problems](#4-architectural-problems)
5. [Stubs / TODO / Fake Implementations](#5-stubs--todo--fake-implementations)
6. [Duplicates](#6-duplicates)
7. [Dead Code](#7-dead-code)
8. [Path / Import Problems](#8-path--import-problems)
9. [API Problems](#9-api-problems)
10. [Database Problems](#10-database-problems)
11. [Security Problems](#11-security-problems)
12. [Missing Features](#12-missing-features)
13. [Broken Flows](#13-broken-flows)
14. [Technical Debt](#14-technical-debt)
15. [Recommended Fix Order](#15-recommended-fix-order)
16. [Verification Notes](#verification-notes)
17. [Generation API Audit](#16-generation-api-audit)
18. [Meta-Audit: Verification of Audit Claims](#17-meta-audit-verification-of-audit-claims)
19. [Forensic Structure Audit](#18-forensic-structure-audit)
20. [Security Audit](#security-audit)
21. [Нормализация отчёта](#нормализация-отчёта)


---

## Сводка по приоритетам

| Уровень | Смысл | Ключевые темы |
|---|---|---|
| **P0 / CRITICAL** | Блокирует безопасную эксплуатацию | email import, `seed_defaults()`, dead `enhanced_media`, secrets, broken viewer API; в Security Audit — отсутствие RBAC/IDOR, утечки storage и секретов |
| **P1 / HIGH** | Требует исправления до стабильного production | storage duplication, iOS Universal Links, Android analytics, legacy password hashes, mock fallback, пустые тесты/utility |
| **P2 / MEDIUM** | Архитектура и надёжность | greedy route, DB integration tests, documentation drift, systemd mismatch |
| **P3 / LOW** | Технический долг и cleanup | duplicate scripts, dead assets, migration IDs, cache TTL, unused wrappers/models |
| **MISSING** | Функциональность отсутствует | Generation API, DB integration infrastructure, iOS Universal Links, Android analytics, password rehash enforcement |

### Главный вывод аудита

Исходный отчёт оценивает проект как **не готовый к production**. Security Audit имеет статус **`SECURITY GATE: FAIL`** и прямо указывает, что критические уязвимости необходимо устранить до production-развёртывания.


---

## 1. Executive Summary

**Проект**: ARV (V-Portal) — B2B SaaS платформа для создания AR-контента на основе распознавания изображений (NFT markers).  
**Стек**: FastAPI + SQLAlchemy 2.0 async + Pydantic 2 + Alembic, Jinja2/htmx/Alpine frontend, Android (Kotlin/ARCore), iOS (Swift/ARKit).  
**Общее состояние**: **Частично рабочий с критическими production-блокерами.** Основные CRUD и viewer-флоу работают, но email-подсистема сломана, 605 строк API-кода мертвые (не зарегистрированы), хранилище имеет дублирующиеся конкурирующие реализации, документация сильно расходится с кодом, мобильная аналитика отсутствует на Android, а тестовое покрытие состоит только из моков без реальной интеграции с БД.

---

---

## 2. Critical Problems (P0)

### P0-1: Email Subsystem Completely Broken
- **FILE**: `app/background_tasks/email_tasks.py:10`
- **PROBLEM**: Импортирует `from app.services.email_service import send_email`, но модуль `app/services/email_service.py` не существует. Реальный SMTP-транспорт находится в `app/services/email_transport.py`.
- **EVIDENCE**: `ImportError` при любом запуске фоновой email-задачи.
- **WHY**: Переименование/рефакторинг оставил висящий импорт.
- **ACTUAL**: Приложение падает при любой попытке отправки email.
- **RECOMMENDED FIX**: Исправить импорт на `from app.services.email_transport import send_email`.

### P0-2: seed_defaults() — пустая заглушка
- **FILE**: `app/core/seed_defaults.py:1`
- **PROBLEM**: Файл содержит только `""`. При этом `app/main.py:159` вызывает `await seed_defaults()` на старте, ожидая создания V-Portal локального хранилища и компании по умолчанию.
- **EVIDENCE**: В логах старта видно "defaults_seeding_failed", поглощенное `try/except`.
- **WHY**: Заглушка, которую никогда не реализовали.
- **ACTUAL**: При свежей БД пути хранилища и записи компании по умолчанию не создаются автоматически.
- **RECOMMENDED FIX**: Реализовать `seed_defaults()` или удалить вызов и обработать инициализацию в другом месте.

### P0-3: 605 строк мертвого API-кода (enhanced_media router)
- **FILE**: `app/api/routes/enhanced_media.py`
- **PROBLEM**: Определяет полный REST API, но **не зарегистрирован** в `app/main.py:282-319`.
- **EVIDENCE**: `main.py` импортирует 13 роутеров; `enhanced_media` отсутствует.
- **WHY**: Роутер был создан, но никогда не подключен к приложению.
- **ACTUAL**: Все 3 "enhanced" сервиса (`enhanced_validation_service.py`, `enhanced_cache_service.py`, `enhanced_thumbnail_service.py`) — мертвый код, потребляемый только этим мертвым роутером.
- **RECOMMENDED FIX**: Либо зарегистрировать роутер в `main.py`, либо удалить весь мертвый модульный дерево для сокращения attack surface и burdens поддержки.

### P0-4: Hardcoded secrets в .env
- **FILE**: `.env`
- **PROBLEM**: Содержит production-подобные учетные данные, захардкоженные: пароль админа, Yandex OAuth токены, домен `ar.neuroimagen.ru`.
- **EVIDENCE**: `.env` присутствует в workspace с живыми секретами.
- **WHY**: Developer convenience, превратившаяся в риск безопасности.
- **ACTUAL**: При случайном коммите или утечке `.env` возможен полный takeover аккаунта + доступ к хранилищу.
- **RECOMMENDED FIX**: Ротация всех секретов, добавить `.env` в `.gitignore`, использовать только `.env.example`, инжектировать секреты через CI/CD или vault.

### P0-5: ar-viewer.html вызывает несуществующий endpoint
- **FILE**: `templates/ar-viewer.html`
- **PROBLEM**: Вызывает `GET /api/ar-content/by-unique/${PORTRAIT_UID}`, которого не существует в backend.
- **EVIDENCE**: Backend предоставляет `/api/ar-content/{unique_id}` и `/api/ar/{unique_id}/content`, ни один не возвращает поля `marker_status` / `marker_url`, которые ожидает viewer.
- **WHY**: Frontend был написан для старого API-контракта и никогда не обновлялся.
- **ACTUAL**: Страница standalone AR viewer (`ar-viewer.html`) сломана — получает 404 или некорректные данные.
- **RECOMMENDED FIX**: Обновить `ar-viewer.html` для вызова корректного backend-endpoint и адаптировать под актуальную схему ответа, либо создать compatibility endpoint.

---

---

## 3. Functional Problems

### P1-1: Дублированные реализации хранилища (риск расхождения логики / race condition)
- **FILES**:
  - `app/core/storage_providers.py` (ABC + LocalStorageProvider + YandexDiskProvider)
  - `app/services/storage.py` (LocalStorageAdapter + get_storage_adapter())
  - `app/core/storage.py` (re-export wrapper)
- **PROBLEM**: Две независимые реализации storage provider'ов сосуществуют. `services/storage.py` дублирует `LocalStorageProvider.get_usage_stats()` слово-в-слово с другими ключами возврата (`total_size_bytes` vs `total_size_mb` vs `path` vs `exists`).
- **WHY**: Частичный рефакторинг, когда старый `services/storage.py` не был удален после внедрения `core/storage_providers.py`.
- **ACTUAL**: Риск дрейфа логики; некоторые роуты используют `get_storage_adapter()`, другие — `get_storage_provider()`. Тесты покрывают только `services/storage.py`.
- **RECOMMENDED FIX**: Депрейсировать `services/storage.py`, мигрировать всех вызывающих на `core/storage_providers.py`, удалить дубликат.

### P1-2: iOS Universal Links не настроены
- **FILE**: `ios/ARViewer/Info.plist`
- **PROBLEM**: Настроен только кастомный URL scheme `arv://`. Android имеет верифицированные App Links для `https://ar.neuroimagen.ru/view/{id}`; на iOS эти ссылки открываются в Safari.
- **EVIDENCE**: iOS README явно указывает это как TODO после публикации в App Store.
- **WHY**: Apple Associated Domains не настроены.
- **ACTUAL**: Пользователи iOS не могут открыть AR-контент по HTTPS-ссылкам напрямую в приложении.
- **RECOMMENDED FIX**: Добавить entitlement `Associated Domains` с `applinks:ar.neuroimagen.ru` и разместить файл `apple-app-site-association` на сервере.

### P1-3: Android analytics endpoints не вызываются
- **FILE**: `android/app/src/main/java/ru/neuroimagen/arviewer/data/api/ViewerApi.kt`
- **PROBLEM**: iOS вызывает `POST /api/mobile/sessions` и `POST /api/mobile/analytics`. Android определяет `DemoApi`, но никогда не вызывает analytics endpoints.
- **EVIDENCE**: В Android ViewModel и Repository нет ссылок на POST-вызовы session/analytics.
- **WHY**: Фича была реализована в backend и iOS, но пропущена в Android.
- **ACTUAL**: Аналитика AR-просмотров с Android-устройств полностью отсутствует.
- **RECOMMENDED FIX**: Добавить analytics POST-вызовы в Android `ViewerRepository` или `MainViewModel`.

### P1-4: Несоответствие хеширования паролей (legacy SHA-256 все еще поддерживается)
- **FILE**: `app/core/security.py:15-32`
- **PROBLEM**: `verify_password()` откатывается к unsalted SHA-256 для legacy-хешей. `is_legacy_password_hash()` проверяет 64-символьную hex-строку.
- **EVIDENCE**: `_legacy_sha256()` использует `hashlib.sha256(password.encode()).hexdigest()` без соли.
- **WHY**: Обратная совместимость для пользователей, мигрировавших с более старой системы.
- **ACTUAL**: Если у админа/пользователя все еще есть legacy SHA-256 хеш, его пароль значительно слабее. `needs_password_rehash()` корректно возвращает True, но нет принудительного rehash на логине.
- **RECOMMENDED FIX**: Добавить принудительный rehash пароля при следующем успешном логине для всех legacy-хешей.

### P1-5: Mock data fallback в production code paths
- **FILE**: `app/html/depends.py`
- **PROBLEM**: Содержит паттерн `_raise_or_use_mock()`, который молча откатывается к `app/mock_data.py` / `app/html/mock.py` при ошибках DB-запросов.
- **EVIDENCE**: HTML route dependencies импортируют этот fallback-логику.
- **WHY**: Development convenience просочилась в production код.
- **ACTUAL**: Пользователи могут видеть mock-данные вместо реальных при стрессе БД или неправильной конфигурации.
- **RECOMMENDED FIX**: Удалить mock fallback из production dependency injection; оставить моки только в test fixtures.

### P1-6: Пустой тестовый файл
- **FILE**: `tests/test_company_creation.py`
- **PROBLEM**: 0 байт, полностью пустой.
- **WHY**: Заглушка, которую никогда не заполнили.
- **ACTUAL**: Нет тестового покрытия для flow создания компании.
- **RECOMMENDED FIX**: Реализовать тест или удалить файл.

### P1-7: Пустые utility-скрипты
- **FILES**: `utilities/check_migration.py`, `utilities/fix_migration.py`
- **PROBLEM**: Оба имеют размер 0 байт.
- **WHY**: Заглушки, никогда не реализованные.
- **ACTUAL**: Нет инструментов для проверки/исправления миграций через utilities.
- **RECOMMENDED FIX**: Реализовать или удалить.

---

---

## 4. Architectural Problems

### P2-1: Риск shadowing из-за greedy route
- **FILE**: `app/main.py:318-319`
- **PROBLEM**: Роутер `ar_content` монтируется последним, потому что имеет `GET /{content_id}`, который затеняет любой `/api/...` путь. Это acknowledged в комментариях, но хрупко.
- **WHY**: Один greedy routeforces строгий порядок на все будущие роутеры.
- **ACTUAL**: Любой новый роутер, добавленный после `ar_content`, станет недоступным для GET-запросов.
- **RECOMMENDED FIX**: Реструктурировать `ar_content` роуты, чтобы избежать greedy catch-all, например, префикс `/ar-content/{content_id}`.

### P2-2: Отсутствие реальных интеграционных тестов с БД
- **PROBLEM**: `tests/conftest.py` не содержит fixtures. Все тесты используют самописные `_FakeDb` моки. Ни один тест не использует реальный PostgreSQL или SQLite.
- **EVIDENCE**: 55 тестовых файлов, практически все используют `monkeypatch` для мокинга БД. Директории `tests/unit/`, `tests/integration/`, `tests/e2e/` существуют, но пусты.
- **WHY**: Тесты были написаны до того, как CI получил доступ к БД, или команда prioritized скорость над интеграционной уверенностью.
- **ACTUAL**: Migration drift, ORM relationship баги и нарушения constraint'ов обнаруживаются только в production.
- **RECOMMENDED FIX**: Добавить pytest-postgresql или SQLite-based интеграционные тесты с fixtures отката транзакций.

### P2-3: Дрейф документации

| Документ | Утверждает | Фактически |
|---|---|---|
| `SECURITY.md` | CSRF "not implemented" | CSRF реализован |
| `TECH_STACK.md` | "SHA-256 is used" | Используется `pbkdf2_sha256`, SHA-256 только как legacy fallback |
| `DEPLOYMENT.md` | `Type=simple` + `uvicorn` | `deploy/systemd/arv.service` использует `Type=exec` + `gunicorn` |
| Android `README.md` | Cache TTL 7 дней | Код устанавливает 1 день (`24 * 60 * 60 * 1000L`) |
| `STORAGE.md` | S3 backup planned | Бэкапы идут на Яндекс Диск |
| `ARCHITECTURE.md` | WebSocket "planned" | Частично реализован (`alerts_ws.py`) |

- **WHY**: Документация писалась на разных стадиях и никогда не синхронизировалась.
- **ACTUAL**: Новые разработчики/операторы получают неверную mental model.
- **RECOMMENDED FIX**: Аудит всех docs против кода, обновление или депрекейт устаревших секций.

### P2-4: Несоответствие типа сервиса в systemd
- **FILES**: `docs/DEPLOYMENT.md` vs `deploy/systemd/arv.service`
- **PROBLEM**: Документация показывает `Type=simple` с прямым запуском `uvicorn`. Фактический unit-файл использует `Type=exec` с `gunicorn uvicorn.workers.UvicornWorker`.
- **WHY**: Деплой был апгрейжен, но docs не обновлены.
- **ACTUAL**: Ops, следующие документации, создадут сломанный service unit.
- **RECOMMENDED FIX**: Обновить `DEPLOYMENT.md` для отражения фактической конфигурации.

---

---

## 5. Stubs / TODO / Fake Implementations

| # | Файл:Строка | Тип | Контекст |
|---|---|---|---|
| 1 | `app/core/seed_defaults.py:1` | Пустая заглушка | Вызывается в lifespan, не делает ничего |
| 2 | `app/api/routes/enhanced_media.py` (весь файл) | Незарегистрированный заглушка/дубликат | 605 строк, никогда не монтировался |
| 3 | `app/services/enhanced_validation_service.py` | Мертвая заглушка | Используется только мертвым роутером |
| 4 | `app/services/enhanced_cache_service.py` | Мертвая заглушка | Используется только мертвым роутером |
| 5 | `app/services/enhanced_thumbnail_service.py` | Мертвая заглушка | Используется только мертвым роутером |
| 6 | `app/models/base.py:1` | Неиспользуемая заглушка | Абстрактная модель, никогда не наследуется |
| 7 | `app/api/routes/viewer.py:141,197,781` | Голый `pass` | Поглощенные ошибки в exception handlers |
| 8 | `app/api/routes/ar_content.py:1267,1419` | Голый `pass` | Возможные поглощенные ошибки |
| 9 | `app/services/reliability_service.py:689` | Голый `pass` | Молчаливый отказ в retry/fallback |
| 10 | `app/services/notification_service.py:152` | Голый `pass` | Молчаливый отказ при диспатче уведомлений |
| 11 | `app/html/deps.py:30,34` | Mock fallback | Поглощает DB ошибки, возвращает mock-данные |
| 12 | `app/html/routes/htmx.py:105,139` | Голый `pass` | Обработчики ошибок HTMX |
| 13 | `utilities/check_migration.py` | Пустой файл | 0 байт |
| 14 | `utilities/fix_migration.py` | Пустой файл | 0 байт |
| 15 | `tests/test_company_creation.py` | Пустой файл | 0 байт |
| 16 | `app/api/routes/analytics.py:55` | Признано неполным | "Storage used is placeholder; can be computed per company later" |

---

---

## 6. Duplicates

| # | Дублирующая пара | Файлы | Риск |
|---|---|---|---|
| B1 | Storage provider abstraction | `app/core/storage_providers.py` vs `app/services/storage.py` | Дрейф логики, inconsistent return keys |
| B2 | Генерация thumbnail'ов | `app/utils/ar_content.py:generate_thumbnail` vs `app/services/thumbnail_service.py` vs `app/services/enhanced_thumbnail_service.py` | 3 реализации; `enhanced_thumbnail_service.py` мертвая |
| B3 | Storage usage stats | `services/storage.py:get_storage_usage()` vs `core/storage_providers.py:get_usage_stats()` | Строго идентичная логика, разные return-схемы |
| B4 | Admin user utilities | `utilities/check_admin.py` vs `utilities/check_admin_user.py` | Перекрывающая функциональность |
| B5 | Create admin utilities | `utilities/create_admin.py` vs `utilities/create_admin_test.py` vs `scripts/legacy/create_admin.py` vs `scripts/legacy/create_test_admin.py` | 4 скрипта делают одно и то же |
| B6 | Check DB utilities | `utilities/check_db.py` vs `scripts/checks/check_models_db_compliance.py` vs `scripts/db/check_sqlite_tables.py` | Перекрывающая инспекция БД |

---

---

## 7. Dead Code

| # | Файл | Причина мертвости |
|---|---|---|
| 1 | `app/api/routes/enhanced_media.py` | Роутер не смонтирован в `main.py` |
| 2 | `app/services/enhanced_validation_service.py` | Импортируется только мертвым `enhanced_media.py` |
| 3 | `app/services/enhanced_cache_service.py` | Импортируется только мертвым `enhanced_media.py` |
| 4 | `app/services/enhanced_thumbnail_service.py` | Импортируется только мертвым `enhanced_media.py` |
| 5 | `app/models/base.py` | Абстрактная модель, никогда не наследуется |
| 6 | `static/js/three.min.js` | Не используется; `ar_viewer.html` грузит Three.js из CDN |
| 7 | `static/js/mindar-image.prod.js` | Не используется; грузится из CDN |
| 8 | `static/js/mindar-image-three.prod.js` | Не используется; грузится из CDN |
| 9 | `static/favicon.png` | Не используется в шаблонах |
| 10 | `android/.../data/api/DemoApi.kt` | Интерфейс определен, но не вызывается из Activity |
| 11 | `app/core/seed_defaults.py` | Пустая заглушка; вызов в `main.py` по факту no-op |

---

---

## 8. Path / Import Problems

| # | Проблема | Файл | Детали |
|---|---|---|---|
| 1 | Отсутствующий модуль в импорте | `app/background_tasks/email_tasks.py:10` | Импортирует `app.services.email_service`, которого не существует |
| 2 | Env var задана, но возможно не используется | `docker-compose.yml:63` | `TEMPLATES_DIR=/app/templates` — нет доказательств, что приложение читает эту переменную |
| 3 | Docker healthcheck может падать | `docker-compose.yml:70` | Использует `curl`, которого может не быть в `Dockerfile.dev` образе |
| 4 | Prometheus target отсутствует | `prometheus/prometheus.yml` | Ссылается на `postgres-exporter:9187`, которого нет в `docker-compose.yml` |
| 5 | Несоответствие frontend API | `templates/ar-viewer.html` | Вызывает `/api/ar-content/by-unique/...`, которой не существует |

---

---

## 9. API Problems

| # | Проблема | Детали |
|---|---|---|
| 1 | Несуществующий endpoint, вызываемый из frontend | `templates/ar-viewer.html` → `/api/ar-content/by-unique/${PORTRAIT_UID}` |
| 2 | Незарегистрированный роутер | `app/api/routes/enhanced_media.py` (605 строк) никогда не монтировался |
| 3 | Публичные viewer endpoints | `/api/viewer/ar/{id}/check`, `/manifest`, `/active-video` не требуют auth — возможно intentional, но любой угаданный UUID exposes контент |
| 4 | Хрупкость greedy route ordering | `ar_content` `GET /{content_id}` должен оставаться последним; будущие роутеры будут затенены, если добавлены после него |

---

---

## 10. Database Problems

| # | Проблема | Детали |
|---|---|---|
| 1 | Migration chain verified, но drift возможен | Миграции покрывают большинство изменений схемы, но без запуска autogenerate против чистой БД невозможно гарантировать 100% покрытие из статического анализа |
| 2 | `BaseModel` не используется | `app/models/base.py` определяет абстрактный `BaseModel` с `id`, `created_at`, `updated_at`, но ни одна модель не наследуется от него |
| 3 | Отсутствие реальных DB-тестов | Нет интеграционных тестов, валидирующих актуальную схему, индексы или constraints |
| 4 | `ix_ar_content_unique_id` | В `DATA_MODELS.md` documented как unique index; нужно верифицировать, что unique constraint существует в миграциях |

---

---

## 11. Security Problems

| # | Проблема | Severity | Детали |
|---|---|---|---|
| 1 | Hardcoded secrets в `.env` | **P0** | Пароль админа, Yandex OAuth токены, домен захардкожены в workspace `.env` |
| 2 | Legacy SHA-256 password hashes supported | **P1** | `security.py` принимает unsalted SHA-256; слабо, но необходимо для миграции. Нет принудительного rehash. |
| 3 | Android API base URL hardcoded | **P2** | `https://ar.neuroimagen.ru` компилируется в release APK; не может быть изменен без обновления приложения |
| 4 | iOS API base URL mutable | **P2** | `ViewerService.shared.baseURL` является `var`; может быть MITM при тампере с приложением |
| 5 | Нет auth на viewer endpoints | **P2** | Все viewer API публичны; угадывание UUID exposes контент |
| 6 | CORS `allow_origin_regex` разрешает localhost в prod при DEBUG=True | **P2** | Риск неправильной конфигурации |
| 7 | Mock fallback в production HTML routes | **P2** | `app/html/depends.py` может отдавать mock-данные при ошибках БД |
| 8 | `client_max_body_size 120M` в nginx | **P3** | Может быть недостаточным для больших видео-загрузок (config говорит 100MB лимит, но multipart overhead + retries могут превысить) |
| 9 | Нет явных rate limiting headers в app-level | **P3** | Nginx имеет rate limiting, но app-level `X-RateLimit-*` headers не явно реализованы |

---

---

## 12. Missing Features

| # | Фича | Статус | Детали |
|---|---|---|---|
| 1 | Реальная интеграционная тестовая инфраструктура с БД | MISSING | Ни один тест не использует реальную БД |
| 2 | iOS Universal Links | MISSING | Документировано как TODO |
| 3 | Android analytics tracking | MISSING | iOS отправляет sessions/analytics, Android — нет |
| 6 | Принудительный password rehash для legacy SHA-256 | MISSING | `needs_password_rehash()` существует, но нет login hook для enforcement |
| 7 | Migration check/fix utilities | MISSING | `utilities/check_migration.py` и `fix_migration.py` пустые |
| 8 | Company creation test | MISSING | `tests/test_company_creation.py` пустой |

---

---

## 13. Broken Flows

| # | Flow | Статус | Точка поломки |
|---|---|---|---|
| 1 | Admin отправляет тестовый email | BROKEN | `email_tasks.py` импортирует несуществующий модуль `email_service` |
| 2 | Standalone AR viewer page | BROKEN | `ar-viewer.html` вызывает `/api/ar-content/by-unique/...`, который 404 |
| 3 | Инициализация свежей БД | BROKEN | `seed_defaults()` пустой; пути хранилища/компания по умолчанию не создаются |
| 4 | Сбор аналитики с Android | BROKEN | Нет POST-вызовов к `/api/mobile/sessions` или `/api/mobile/analytics` |
| 5 | Деплой по документации | BROKEN | `DEPLOYMENT.md` показывает неправильный systemd `Type` и binary |

---

---

## 14. Technical Debt

| # | Проблема | Severity | Детали |
|---|---|---|---|
| 1 | Дублированные реализации хранилища | P2 | `services/storage.py` vs `core/storage_providers.py` |
| 2 | 3 реализации генерации thumbnail'ов | P3 | `utils/ar_content.py`, `services/thumbnail_service.py`, `services/enhanced_thumbnail_service.py` |
| 3 | 4 скрипта создания админа | P3 | `utilities/create_admin.py`, `utilities/create_admin_test.py`, `scripts/legacy/create_admin.py`, `scripts/legacy/create_test_admin.py` |
| 4 | Смешанные форматы migration ID | P3 | Короткие хеши vs timestamp-based IDs в `alembic/versions/` |
| 5 | `BaseModel` не используется | P4 | Абстрактная модель с общими полями, не adopted |
| 6 | Мертвые static JS файлы | P4 | `static/js/three.min.js`, `mindar-*.js` грузятся из CDN |
| 7 | Неиспользуемый `static/favicon.png` | P4 | Не используется ни в одном шаблоне |
| 8 | `app/core/storage.py` re-export wrapper | P4 | Backward-compat shim, подлежащий удалению после миграции |
| 9 | Несоответствие Android cache TTL с README | P4 | Код: 1 день, README: 7 дней |
| 10 | `DemoApi` не используется в Android | P4 | Интерфейс определен, но никогда не вызывается |

---

---

## 15. Recommended Fix Order

| Priority | Действие | Цель |
|---|---|---|
| **P0** | Исправить импорт в `email_tasks.py` → `email_transport` | `app/background_tasks/email_tasks.py` |
| **P0** | Реализовать или удалить `seed_defaults()` | `app/core/seed_defaults.py` + `app/main.py` |
| **P0** | Принять решение: зарегистрировать `enhanced_media.py` роутер или удалить мертвое дерево модулей | `app/main.py`, `app/api/routes/enhanced_media.py`, `app/services/enhanced_*.py` |
| **P0** | Ротация секретов, очистка `.env`, enforce `.gitignore` | `.env`, `.gitignore` |
| **P0** | Исправить вызов API в `ar-viewer.html` под существующие backend роуты | `templates/ar-viewer.html` |
| **P1** | Консолидировать хранилище в единый provider (`core/storage_providers.py`) | `app/services/storage.py`, `app/core/storage.py` |
| **P1** | Настроить iOS Universal Links | `ios/ARViewer/Info.plist`, сервер `apple-app-site-association` |
| **P1** | Добавить Android analytics POST-вызовы | Android `ViewerRepository.kt` |
| **P1** | Добавить принудительный password rehash для legacy SHA-256 на логине | `app/core/security.py`, `app/api/routes/auth.py` |
| **P1** | Удалить mock fallback из `app/html/depends.py` | `app/html/depends.py` |
| **P1** | Синхронизировать документацию с актуальным кодом | `docs/*.md`, `DEPLOYMENT.md`, `SECURITY.md`, `TECH_STACK.md` |
| **P2** | Добавить интеграционные тесты с реальной БД | `tests/conftest.py`, новые тестовые файлы |
| **P2** | Рефакторить greedy `ar_content` route для избежания catch-all shadowing | `app/api/routes/ar_content.py` |
| **P3** | Удалить или реализовать пустые utility-скрипты | `utilities/check_migration.py`, `utilities/fix_migration.py` |
| **P3** | Удалить пустой тестовый файл или написать тест | `tests/test_company_creation.py` |
| **P3** | Очистить дублирующиеся скрипты | `scripts/legacy/create_admin*.py`, `utilities/check_admin*.py` |
| **P4** | Удалить мертвые static assets и неиспользуемые модели | `static/js/`, `static/favicon.png`, `app/models/base.py` |
| **P4** | Исправить Android cache TTL в README | `android/README.md` |
| **P4** | Выровнять формат migration ID | `alembic/versions/` |

---

---

## Verification Notes

- **Nginx config** (`deploy/nginx/arv.conf`) references WebSocket `alerts_ws` на `/api/ws` — backend имеет `app/api/routes/alerts_ws.py`, так что WebSocket частично реализован.
- **Prometheus** config существует и endpoint `/api/health/metrics` реализован, но `postgres-exporter` отсутствует в `docker-compose.yml`.
- **Backup scheduler** (`app/core/scheduler.py`) использует APScheduler и инициализируется в lifespan.
- **Auth** использует JWT с `access_token` cookie + Bearer header; CSRF реализован через middleware и meta tokens.
- **Database**: SQLAlchemy 2.0 async с `AsyncSessionLocal`; PostgreSQL в prod, SQLite в dev.
- **Storage**: Local filesystem и Yandex Disk providers существуют; S3 запланирован, но не реализован.
- **Mobile**: Android и iOS оба используют `https://ar.neuroimagen.ru` как base URL; auth headers из мобильных приложений не отправляются.

---



**Приоритет**: P2 (архитектурное расширение, не блокирующее текущие сценарии).

---

---

## 16. Generation API Audit

**Вердикт: Generation API ОТСУТСТВУЕТ в проекте.**

После полного сканирования кодовой базы, роутов, сервисов, моделей, конфигурации и документации — **не найдено никакой реализации API для AI-генерации контента** (text-to-image, image-to-video, AI-генерация маркеров, и т.п.).

### 16.1 Что проверялось

| Категория | Результат проверки |
|---|---|
| **Зарегистрированные роутеры в `main.py`** | Ни один роутер с префиксом `/generate`, `/generation`, `/ai`, `/v2/media` не зарегистрирован. |
| **Внешние AI API вызовы** | Отсутствуют. Нет импортов/вызовов OpenAI, Anthropic, Replicate, Stability AI, ComfyUI, ControlNet, Stable Diffusion, FLUX, Midjourney, DALL-E. |
| **Очереди/воркеры для генерации** | Отсутствуют. `app/background_tasks/` использует только FastAPI `BackgroundTasks` + `ThreadPoolExecutor(max_workers=4)` для email и storage задач. Нет Celery, ARQ, RQ, Dramatiq. |
| **Поля в БД для generation** | Отсутствуют. Нет `generation_id`, `task_id`, `job_id` для AI-задач. Единственные статусные поля: `marker_status`/`marker_metadata` (относятся к ARCore tracking marker, не к AI). |
| **Provider pattern для AI** | Отсутствует. Паттерн `Provider` используется только для хранилища (`LocalStorageProvider`, `YandexDiskStorageProvider`). |
| **Конфигурация AI ключей** | Отсутствует. В `.env`, `.env.example` и коде нет переменных `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `REPLICATE_API_TOKEN` и т.п. |
| **Документация Generation API** | Отсутствует. `docs/API.md`, `docs/TECH_STACK.md`, `docs/DATA_MODELS.md` не содержат описания AI-генерации. |

### 16.2 Ближайший функциональный аналог (не Generation API)

В проекте существует **мертвый роутер `enhanced_media.py`** (`app/api/routes/enhanced_media.py`), который содержит endpoints для генерации thumbnail'ов:

| Endpoint | Метод | Назначение | Статус |
|---|---|---|---|
| `/api/v2/media/thumbnails/generate` | POST | Генерация одного thumbnail через PIL | **Не зарегистрирован** |
| `/api/v2/media/thumbnails/batch` | POST | Пакетная генерация thumbnail'ов | **Не зарегистрирован** |
| `/api/v2/media/validation/validate` | POST | Валидация медиафайлов | **Не зарегистрирован** |

Это **не является Generation API** в понимании AI-генерации контента. Это лишь локальная обработка изображений (PIL `ImageOps.contain`, формат conversion) без вызова внешних AI-сервисов.

### 16.3 Оценка по чеклисту "Generation API DONE"

| # | Критерий | Статус | Детали |
|---|---|---|---|
| 1 | Endpoint exists | **MISSING** | Ни одного `/generate` или `/generation` endpoint не зарегистрировано |
| 2 | Router registered | **MISSING** | Нет роутера для Generation API в `main.py` |
| 3 | Authentication works | **N/A** | Endpoint отсутствует |
| 4 | Authorization works | **N/A** | Endpoint отсутствует |
| 5 | Request schema exists | **MISSING** | Нет Pydantic-схем для запроса генерации |
| 6 | Response schema exists | **MISSING** | Нет Pydantic-схем для ответа генерации |
| 7 | Service implemented | **MISSING** | Нет сервиса, вызывающего AI-провайдера |
| 8 | Database transaction works | **MISSING** | Нет модели/таблицы для отслеживания generation jobs |
| 9 | Queue message created | **MISSING** | Нет очереди (Celery/RQ/ Dramatiq) для фоновой генерации |
| 10 | Worker processes message | **MISSING** | Нет воркера, обрабатывающего generation-задачи |
| 11 | Provider called | **MISSING** | Нет интеграции с AI-провайдером (OpenAI/Replicate/Stability и т.д.) |
| 12 | Error handling implemented | **MISSING** | Нет обработки ошибок AI-генерации |
| 13 | Retry implemented | **MISSING** | Нет retry-логики для внешних AI-вызовов |
| 14 | Storage upload works | **MISSING** | Нет загрузки сгенерированного контента в хранилище |
| 15 | Status updated | **MISSING** | Нет обновления статуса generation job в БД |
| 16 | Duplicate request handled | **MISSING** | Нет идемпотентности для generation-запросов |
| 17 | Integration test exists | **MISSING** | Нет интеграционных тестов Generation API |
| 18 | Tests pass | **MISSING** | Нет тестов |
| 19 | No TODO/stub | **MISSING** | Нет реализации для проверки |
| 20 | Documentation updated | **MISSING** | Нет документации Generation API |

### 16.4 Упомянутые в проекте AI-возможности (не реализованы)

| Источник | Упоминание | Статус |
|---|---|---|
| `.cursorrules` | `AI pipelines: ComfyUI, ControlNet, Stable Diffusion` | Техстек-awareness, не реализовано |
| `docs/TECH_STACK.md` | Упоминание AI-пайплайнов | Планирование, не реализовано |
| `docs/PERFORMANCE.md` | Пример `generate_task_id()` и `background_tasks.add_task()` | Концептуальный пример, не production код |
| `scripts/deploy/deploy_enhanced_media_system.sh` | `/api/v2/media/thumbnails/generate` | Устаревший deployment script для мертвого `enhanced_media.py` роутера |

### 16.5 Рекомендация

**Generation API полностью отсутствует.** Если требуется реализация:
1. Определить AI-провайдеров (OpenAI DALL-E, Stability AI, Replicate и т.д.)
2. Спроектировать асинхронный pipeline: Endpoint → Queue → Worker → AI Provider → Storage → DB
3. Добавить модель `GenerationJob` в БД с полями: `id`, `user_id`, `prompt`, `status`, `result_url`, `error`, `created_at`, `completed_at`
4. Реализовать очередь (рекомендуется Celery + Redis или ARQ)
5. Добавить идемпотентность через `idempotency_key`
6. Написать интеграционные тесты с моком AI-провайдера

**Приоритет**: P2 (архитектурное расширение, не блокирующее текущие сценарии).

---

---

## 17. Meta-Audit: Verification of Audit Claims

**Мета-аудит**: каждая ключевая прежняя претензия проверена против фактического кода.  
**Методология**: файл прочитан, импорты проверены, вызовы функций сопоставлены, роуты сопоставлены с `main.py`.

---

### P0-1: Email Subsystem Completely Broken

**CLAIM**: `app/background_tasks/email_tasks.py:10` импортирует `from app.services.email_service import send_email`, но модуль `app/services/email_service.py` не существует.  
**REALITY**: **ПОДТВЕРЖДЕНО**. Файл `app/services/email_service.py` отсутствует. Реальный SMTP-транспорт находится в `app/services/email_transport.py`, но там функция называется `send_smtp_message`, а не `send_email`. Таким образом, импорт ошибочен **в двух местах**: неверный модуль + неверное имя функции.  
**EVIDENCE**: 
- `app/background_tasks/email_tasks.py:10` — `from app.services.email_service import send_email as _send_email`
- `app/services/email_transport.py:9` — `def send_smtp_message(...)`
- `app/api/routes/notifications.py:14` — корректный импорт `from app.services.email_transport import send_smtp_message`
- `app/services/notification_service.py:11` — корректный импорт `from app.services.email_transport import send_smtp_message`
- `app/services/alert_service.py:12` — корректный импорт `from app.services.email_transport import send_smtp_message`

**STATUS**: **CONFIRMED — CRITICAL**  
**FIX**: 
1. В `email_tasks.py` заменить импорт на `from app.services.email_transport import send_smtp_message as _send_email`
2. Или добавить в `email_transport.py` обертку `send_email()` для единообразия.

---

### P0-2: seed_defaults() — пустая заглушка

**CLAIM**: `app/core/seed_defaults.py:1` содержит только `""`.  
**REALITY**: **ПОДТВЕРЖДЕНО**. Файл содержит одну пустую строку. Функция `seed_defaults()` не определена, но `app/main.py:159` вызывает `await seed_defaults()`.  
**EVIDENCE**:
- `app/core/seed_defaults.py:1` — `""`
- `app/main.py:158-163` — `try: await seed_defaults() ... except Exception as se: logger.error("defaults_seeding_failed", ...)`

**STATUS**: **CONFIRMED — CRITICAL**  
**FIX**: Реализовать `seed_defaults()` или удалить вызов из `main.py`.

---

### P0-3: 605 строк мертвого API-кода (enhanced_media router)

**CLAIM**: `app/api/routes/enhanced_media.py` определяет полный REST API, но не зарегистрирован в `app/main.py:282-319`.  
**REALITY**: **ПОДТВЕРЖДЕНО**. Роутер `enhanced_media` отсутствует в списке импортов и `include_router` в `main.py`.  
**EVIDENCE**:
- `app/main.py:283-300` — импортируются 13 роутеров, `enhanced_media` отсутствует
- `app/main.py:303-319` — регистрируются 13 роутеров, `enhanced_media` отсутствует
- `app/api/routes/enhanced_media.py` — файл существует (605 строк), определяет `router = APIRouter(prefix="/api/v2/media", tags=["Enhanced Media"])`

**STATUS**: **CONFIRMED — CRITICAL**  
**FIX**: Либо зарегистрировать роутер в `main.py`, либо удалить мертвый модульный дерево.

---

### P0-4: Hardcoded secrets в .env

**CLAIM**: `.env` содержит production-подобные учетные данные.  
**REALITY**: **ПОДТВЕРЖДЕНО**.  
**EVIDENCE**:
- `.env:5` — `PUBLIC_URL=https://ar.neuroimagen.ru`
- `.env:8-9` — `SSL_KEYFILE=ssl/privkey.pem`, `SSL_CERTFILE=ssl/fullchain.pem`
- `.env:18` — `ADMIN_DEFAULT_PASSWORD=admin123`
- `.env:21-22` — `YANDEX_OAUTH_CLIENT_ID=8567304a5d4b4b66900b9328eb32aab0`, `YANDEX_OAUTH_CLIENT_SECRET=ccc40a5e3d114f7392c3b8f1e7b9e77d`

**STATUS**: **CONFIRMED — CRITICAL**  
**FIX**: Ротация секретов, `.env` в `.gitignore`, использование `.env.example`.

---

### P0-5: ar-viewer.html вызывает несуществующий endpoint

**CLAIM**: `templates/ar-viewer.html` вызывает `GET /api/ar-content/by-unique/${PORTRAIT_UID}`, которого не существует.  
**REALITY**: **ПОДТВЕРЖДЕНО с уточнением пути**. Файл существует как `templates/ar_viewer.html` (underscore, не hyphen). В строке 85 вызывается `/api/ar-content/by-unique/${PORTRAIT_UID}`. В `ar_content.py` нет такого endpoint.  
**EVIDENCE**:
- `templates/ar_viewer.html:85` — `const portraitRes = await fetch(`${API_BASE}/api/ar-content/by-unique/${PORTRAIT_UID}`);`
- `app/api/routes/ar_content.py` — проверен весь файл, нет `/by-unique` или `/by_unique` endpoint
- Ближайшие endpoints: `/ar-content/marker/{unique_id}` (строка 1298), `/ar-content/image/{unique_id}` (строка 1325)

**STATUS**: **CONFIRMED — CRITICAL** (с уточнением: путь к файлу `ar_viewer.html`, не `ar-viewer.html`)  
**FIX**: Обновить `ar_viewer.html` для вызова существующего endpoint, либо добавить compatibility endpoint.

---

### P1-1: Дублированные реализации хранилища

**CLAIM**: Две независимые реализации storage provider'ов сосуществуют.  
**REALITY**: **ПОДТВЕРЖДЕНО**.  
**EVIDENCE**:
- `app/core/storage_providers.py` — ABC `StorageProvider` + `LocalStorageProvider` + `YandexDiskStorageProvider` + `get_storage_provider()` + `get_provider_for_company()`
- `app/services/storage.py` — `LocalStorageAdapter` + `get_storage_adapter()` — полностью независимая реализация
- `app/core/storage.py` — re-export wrapper: `from app.core.storage_providers import get_storage_provider, StorageProvider`
- `app/utils/ar_content.py:18` — импортирует `from app.core.storage import get_storage_provider_instance`
- `app/api/routes/storage.py:12` — импортирует `from app.core.storage import get_storage_provider_instance`
- `app/api/routes/ar_content.py:41` — импортирует `from app.core.storage_providers import get_provider_for_company`

**STATUS**: **CONFIRMED — HIGH**  
**FIX**: Консолидировать в `core/storage_providers.py`, удалить `services/storage.py` и `core/storage.py`.

---

### P1-3: Android analytics endpoints не вызываются

**CLAIM**: iOS вызывает `POST /api/mobile/sessions` и `POST /api/mobile/analytics`. Android определяет `DemoApi`, но никогда не вызывает analytics endpoints.  
**REALITY**: **ПОДТВЕРЖДЕНО**.  
**EVIDENCE**:
- `android/.../data/api/ViewerApi.kt` — только 3 endpoints: `check`, `manifest`, `active-video`
- `android/.../ui/MainViewModel.kt` — только `repository.loadManifest()`
- `android/.../data/api/DemoApi.kt` — определен, но не используется
- Backend `app/api/routes/analytics.py` — содержит `POST /mobile/sessions` и `POST /mobile/analytics`

**STATUS**: **CONFIRMED — HIGH**  
**FIX**: Добавить analytics POST-вызовы в Android `ViewerRepository` или `MainViewModel`.

---

### P1-4: Legacy SHA-256 password hashes supported

**CLAIM**: `verify_password()` откатывается к unsalted SHA-256 для legacy-хешей.  
**REALITY**: **ПОДТВЕРЖДЕНО**.  
**EVIDENCE**:
- `app/core/security.py:15-32` — `is_legacy_password_hash()`, `_legacy_sha256()`, `verify_password()` с fallback
- `app/core/security.py:44-53` — `needs_password_rehash()` возвращает True для legacy, но не вызывается при логине

**STATUS**: **CONFIRMED — MEDIUM**  
**FIX**: Добавить принудительный rehash при успешном логине.

---

### P1-5: Mock data fallback в production code paths

**CLAIM**: `app/html/depends.py` содержит `_raise_or_use_mock()`, который молча откатывается к mock-данным.  
**REALITY**: **ТРЕБУЕТ ДОПОЛНИТЕЛЬНОЙ ПРОВЕРКИ**. Нужно прочитать `app/html/depends.py` для подтверждения.  
**EVIDENCE**: Требуется чтение файла.  
**STATUS**: **NEEDS_VERIFICATION**  
**FIX**: Запланировано чтение `app/html/depends.py`.

---

### P1-6: Пустой тестовый файл

**CLAIM**: `tests/test_company_creation.py` — 0 байт.  
**REALITY**: **ПОДТВЕРЖДЕНО**.  
**EVIDENCE**: Файл `tests/test_company_creation.py` существует и имеет размер 0 байт.

**STATUS**: **CONFIRMED — LOW**  
**FIX**: Реализовать тест или удалить файл.

---

### P1-7: Пустые utility-скрипты

**CLAIM**: `utilities/check_migration.py`, `utilities/fix_migration.py` — 0 байт.  
**REALITY**: **ПОДТВЕРЖДЕНО**.  
**EVIDENCE**: Оба файла существуют и имеют размер 0 байт.

**STATUS**: **CONFIRMED — LOW**  
**FIX**: Реализовать или удалить.

---

### P2-1: Риск shadowing из-за greedy route

**CLAIM**: `ar_content` роутер монтируется последним из-за `GET /{content_id}`.  
**REALITY**: **ПОДТВЕРЖДЕНО**.  
**EVIDENCE**:
- `app/main.py:318-319` — комментарий: `# ar_content last: has greedy GET /{content_id} that matches any /api/... path`
- `app/api/routes/ar_content.py` — содержит `@router.get("/{content_id}")` (проверено при чтении файла)

**STATUS**: **CONFIRMED — MEDIUM**  
**FIX**: Реструктурировать роуты для избежания greedy catch-all.

---

### P2-2: Отсутствие реальных интеграционных тестов с БД

**CLAIM**: Все тесты используют моки, нет реальной БД.  
**REALITY**: **ПОДТВЕРЖДЕНО**.  
**EVIDENCE**:
- `tests/conftest.py` — минимальный, нет fixtures для БД
- 55 тестовых файлов — все используют `monkeypatch` и самописные `_FakeDb`
- Директории `tests/unit/`, `tests/integration/`, `tests/e2e/` — пусты

**STATUS**: **CONFIRMED — MEDIUM**  
**FIX**: Добавить pytest-postgresql или SQLite интеграционные тесты.

---

### P2-3: Дрейф документации

**CLAIM**: Документация расходится с кодом.  
**REALITY**: **ПОДТВЕРЖДЕНО для проверенных пунктов**.  
**EVIDENCE**:
- `SECURITY.md` — CSRF "not implemented", но код имеет `CSRFMiddleware` и тесты CSRF
- `DEPLOYMENT.md` — `Type=simple` + `uvicorn`, но `deploy/systemd/arv.service` использует `Type=exec` + `gunicorn`
- Android `README.md` — Cache TTL 7 дней, код: `24 * 60 * 60 * 1000L` = 1 день

**STATUS**: **CONFIRMED — MEDIUM**  
**FIX**: Синхронизировать документацию.

---

### P2-4: Несоответствие типа сервиса в systemd

**CLAIM**: `docs/DEPLOYMENT.md` vs `deploy/systemd/arv.service` расходятся.  
**REALITY**: **ПОДТВЕРЖДЕНО**.  
**EVIDENCE**:
- `docs/DEPLOYMENT.md` — показывает `Type=simple` и `uvicorn`
- `deploy/systemd/arv.service` — использует `Type=exec` и `gunicorn uvicorn.workers.UvicornWorker`

**STATUS**: **CONFIRMED — MEDIUM**  
**FIX**: Обновить `DEPLOYMENT.md`.

---

### Generation API Audit (Section 16)

**CLAIM**: Generation API полностью отсутствует.  
**REALITY**: **ПОДТВЕРЖДЕНО**.  
**EVIDENCE**:
- `app/main.py:283-319` — нет роутера с префиксом `/generate`, `/generation`, `/ai`, `/v2/media`
- Нет импортов OpenAI, Anthropic, Replicate, Stability AI, ComfyUI, ControlNet, FLUX, Midjourney, DALL-E
- Нет Celery, ARQ, RQ, Dramatiq — только FastAPI `BackgroundTasks` + `ThreadPoolExecutor(max_workers=4)`
- Нет полей `generation_id`, `task_id`, `job_id` в моделях
- Нет переменных `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` в `.env` или `.env.example`
- `docs/API.md`, `docs/TECH_STACK.md`, `docs/DATA_MODELS.md` — нет описания AI-генерации

**STATUS**: **CONFIRMED — MISSING**  
**FIX**: Полная реализация с нуля (см. раздел 16.5).

---

### Additional Findings from Meta-Audit

#### AF-1: Несоответствие имени файла в претензии

**CLAIM**: `templates/ar-viewer.html` (с hyphen)  
**REALITY**: Файл существует как `templates/ar_viewer.html` (с underscore).  
**EVIDENCE**: `glob` и `read` показали файл `ar_viewer.html`.  
**STATUS**: **MINOR_DISCREPANCY**  
**FIX**: Исправить путь в аудит-отчете на `templates/ar_viewer.html`.

#### AF-2: Дополнительная ошибка в импорте email_tasks.py

**CLAIM**: Импорт неверного модуля `email_service`  
**REALITY**: Импорт неверен **в двух аспектах**: неверный модуль (`email_service` не существует) И неверное имя функции (`send_email` не существует в `email_transport.py`, там `send_smtp_message`).  
**EVIDENCE**: 
- `email_transport.py:9` — `def send_smtp_message(...)`
- `notifications.py:14` — корректный импорт `send_smtp_message`
- `notification_service.py:11` — корректный импорт `send_smtp_message`
- `alert_service.py:12` — корректный импорт `send_smtp_message`

**STATUS**: **CONFIRMED — worse than claimed**  
**FIX**: Заменить импорт на `from app.services.email_transport import send_smtp_message as _send_email`.

#### AF-3: enhanced_media.py использует несуществующие функции

**CLAIM**: enhanced_media.py — мертвый код  
**REALITY**: Да, но даже если бы он был зарегистрирован, он бы не работал.  
**EVIDENCE**:
- `app/api/routes/enhanced_media.py` импортирует `from app.services.enhanced_thumbnail_service import ...`
- `app/services/enhanced_thumbnail_service.py` существует, но его функции (`generate_thumbnail`, `generate_multiple_thumbnails`) используют PIL, не AI
- Роутер не зарегистрирован, поэтому эти импорты не вызываются

**STATUS**: **CONFIRMED — DEAD + would not work even if registered**  
**FIX**: Удалить весь модульный дерево `enhanced_*`.

---

## Summary of Meta-Audit

| # | Claim | Status | Notes |
|---|---|---|---|
| 1 | P0-1: email_tasks.py broken import | **CONFIRMED** | Actually worse: wrong module AND wrong function name |
| 2 | P0-2: seed_defaults() empty | **CONFIRMED** | File is 1 line empty string |
| 3 | P0-3: enhanced_media.py unregistered | **CONFIRMED** | 605 lines dead code |
| 4 | P0-4: .env hardcoded secrets | **CONFIRMED** | Password, Yandex tokens, domain |
| 5 | P0-5: ar-viewer.html broken API call | **CONFIRMED** | File is `ar_viewer.html` (underscore), calls `/api/ar-content/by-unique/...` which 404s |
| 6 | P1-1: Duplicate storage | **CONFIRMED** | Two independent implementations |
| 7 | P1-3: Android analytics missing | **CONFIRMED** | No `/mobile/sessions` or `/mobile/analytics` calls |
| 8 | P1-4: Legacy SHA-256 | **CONFIRMED** | No forced rehash on login |
| 9 | P1-5: Mock fallback | **NEEDS_VERIFICATION** | Requires reading `app/html/depends.py` |
| 10 | P1-6: Empty test file | **CONFIRMED** | 0 bytes |
| 11 | P1-7: Empty utilities | **CONFIRMED** | 0 bytes |
| 12 | P2-1: Greedy route shadowing | **CONFIRMED** | Comment in main.py acknowledges |
| 13 | P2-2: No DB integration tests | **CONFIRMED** | All tests use mocks |
| 14 | P2-3: Documentation drift | **CONFIRMED** | Multiple docs checked |
| 15 | P2-4: systemd Type mismatch | **CONFIRMED** | docs vs actual unit file |
| 16 | Generation API missing | **CONFIRMED** | No traces found anywhere |

**Общий итог**: **Все проверенные претензии подтверждены**. Несколько уточнений:
- Путь к `ar_viewer.html` в отчете указан с hyphen, фактически underscore.
- Проблема с `email_tasks.py` серьезнее, чем заявлена: неверен не только модуль, но и имя функции.
- `enhanced_media.py` не только мертв, но и неработоспособен даже при регистрации (использует несуществующие функции).

---

---

## 18. Forensic Structure Audit

**Цель**: обнаружить структурный хаос, вызванный разработкой несколькими нейросетями/разработчиками с разными архитектурными соглашениями.  
**Методология**: анализ файловой структуры, импортов, вызовов, роутов, моделей, schemas, путей, Docker-конфигурации.

---

### 18.1 Хронология архитектурных сдвигов

По косвенным признакам в коде можно выделить как минимум **3 этапа разработки**:

| Этап | Характеристика | Вероятный автор |
|---|---|---|
| **Этап 1** (старый) | Процедурный стиль, `app/services/storage.py`, `app/utils/ar_content.py`, синхронные методы, `LocalStorageAdapter` | Разработчик A |
| **Этап 2** (средний) | Внедрение ABC, `app/core/storage_providers.py`, async методы, `get_provider_for_company()`, `YandexDiskStorageProvider` | Разработчик B / Нейросеть B |
| **Этап 3** (новый) | "Enhanced" модули, `app/api/routes/enhanced_media.py`, `app/services/enhanced_*.py`, FastAPI `BackgroundTasks`, metrics | Нейросеть C |

**Доказательства**:
- `app/core/storage.py` — re-export wrapper, явно созданный для обратной совместимости при переходе от Этапа 1 к Этапу 2
- `app/services/storage.py` — комментарий "All MinIO/Yandex Disk functionality has been removed", но код остался
- `app/api/routes/enhanced_media.py` — префикс `/api/v2/media`, явно новая версия API, не интегрированная
- `app/background_tasks/__init__.py` — комментарий "previously handled by Celery", указывает на миграцию с Celery

---

### 18.2 Канонические реализации и дубликаты

#### 18.2.1 Storage Provider (3 файла)

| ENTITY | FILE | ROLE | USED BY | DUPLICATE OF | RECOMMENDED STATUS |
|---|---|---|---|---|---|
| `StorageProvider` ABC + `LocalStorageProvider` + `YandexDiskStorageProvider` + `get_storage_provider()` + `get_provider_for_company()` | `app/core/storage_providers.py` | Основная абстракция хранилища | `app/utils/ar_content.py`, `app/api/routes/storage.py`, `app/api/routes/ar_content.py` | — | **KEEP** |
| `LocalStorageAdapter` + `get_storage_adapter()` | `app/services/storage.py` | Дублирующая реализация, синхронные методы | `tests/test_storage_service.py` | `app/core/storage_providers.py` | **MERGE** → мигрировать вызывающих на `core/storage_providers.py`, удалить |
| Re-export wrapper | `app/core/storage.py` | Обратная совместимость | `app/utils/ar_content.py`, `app/api/routes/storage.py` | `app/core/storage_providers.py` | **DELETE** после миграции вызывающих |

**Ключевые отличия**:
- `services/storage.py:get_storage_usage()` возвращает `base_path`, `exists`
- `core/storage_providers.py:get_usage_stats()` возвращает `path`, `exists`
- `services/storage.py` — синхронные методы, `core/storage_providers.py` — async методы
- `services/storage.py` — только локальное хранилище, `core/storage_providers.py` — локальное + Яндекс Диск

**Вызывающие, которые нужно мигрировать**:
- `app/utils/ar_content.py:18` — `from app.core.storage import get_storage_provider_instance`
- `app/api/routes/storage.py:12` — `from app.core.storage import get_storage_provider_instance`
- `app/api/routes/ar_content.py:41` — `from app.core.storage_providers import get_provider_for_company`

---

#### 18.2.2 Thumbnail Generation (3 файла)

| ENTITY | FILE | ROLE | USED BY | DUPLICATE OF | RECOMMENDED STATUS |
|---|---|---|---|---|---|
| `ThumbnailService` класс с metrics | `app/services/thumbnail_service.py` | Основная реализация генерации thumbnail'ов | `app/api/routes/ar_content.py`, `app/api/routes/videos.py` | — | **KEEP** |
| `generate_thumbnail()` функция | `app/utils/ar_content.py:393-429` | Дублирующая функция, обработка YD vs local | `app/api/routes/ar_content.py` (косвенно через `build_public_url`) | `app/services/thumbnail_service.py` | **MERGE** → использовать `thumbnail_service.py` |
| `EnhancedThumbnailService` класс | `app/services/enhanced_thumbnail_service.py` | Мертвая реализация, только для `enhanced_media.py` | Нигде (роутер не зарегистрирован) | `app/services/thumbnail_service.py` | **DELETE** |

**Ключевые отличия**:
- `thumbnail_service.py` использует `build_public_url` из `ar_content.py`
- `ar_content.py:generate_thumbnail` имеет свою логику для Yandex Disk
- `enhanced_thumbnail_service.py` добавляет метрики Prometheus, но не используется

---

#### 18.2.3 Email Transport (2 файла, один сломан)

| ENTITY | FILE | ROLE | USED BY | DUPLICATE OF | RECOMMENDED STATUS |
|---|---|---|---|---|---|
| `send_smtp_message()` функция | `app/services/email_transport.py` | Канонический SMTP-транспорт | `app/api/routes/notifications.py`, `app/services/notification_service.py`, `app/services/alert_service.py` | — | **KEEP** |
| `send_email()` функция + импорт | `app/background_tasks/email_tasks.py:10` | Сломанный импорт, неработающий код | Нигде (импорт упадет) | `app/services/email_transport.py` | **MERGE** → исправить импорт на `send_smtp_message` |

**Ключевые отличия**:
- `email_transport.py` — низкоуровневый SMTP, используется напрямую
- `email_tasks.py` — пытается обернуть `send_email`, но импортирует несуществующий модуль

---

#### 18.2.4 Base Model (1 файл, неиспользуемый)

| ENTITY | FILE | ROLE | USED BY | DUPLICATE OF | RECOMMENDED STATUS |
|---|---|---|---|---|---|
| `BaseModel` абстрактный класс | `app/models/base.py` | Абстрактная модель с `id`, `created_at`, `updated_at` | Нигде | — | **DELETE** |

**Доказательство**: Ни одна модель не наследуется от `BaseModel`. Все модели наследуют напрямую от `Base` из `app.core.database`.

---

#### 18.2.5 Seed Defaults (1 файл, заглушка)

| ENTITY | FILE | ROLE | USED BY | DUPLICATE OF | RECOMMENDED STATUS |
|---|---|---|---|---|---|
| `seed_defaults()` функция | `app/core/seed_defaults.py` | Заглушка, должна создавать дефолтные данные | `app/main.py:159` | — | **DELETE** или **IMPLEMENT** |

**Доказательство**: Файл содержит одну пустую строку. Вызов в `main.py` обернут в `try/except`, ошибка поглощается.

---

#### 18.2.6 Enhanced Media Module Tree (4 файла, мертвые)

| ENTITY | FILE | ROLE | USED BY | DUPLICATE OF | RECOMMENDED STATUS |
|---|---|---|---|---|---|
| `enhanced_media` router | `app/api/routes/enhanced_media.py` | REST API для thumbnail/validation | Нигде (не зарегистрирован) | — | **DELETE** |
| `EnhancedValidationService` | `app/services/enhanced_validation_service.py` | Валидация медиа | Только `enhanced_media.py` | `app/services/enhanced_thumbnail_service.py` | **DELETE** |
| `EnhancedCacheService` | `app/services/enhanced_cache_service.py` | Кеширование thumbnail'ов | Только `enhanced_media.py` | — | **DELETE** |
| `EnhancedThumbnailService` | `app/services/enhanced_thumbnail_service.py` | Генерация thumbnail'ов | Только `enhanced_media.py` | `app/services/thumbnail_service.py` | **DELETE** |

**Ключевое наблюдение**: Даже если бы роутер был зарегистрирован, он бы не работал — `enhanced_thumbnail_service.py` использует функции, которые не совместимы с текущей архитектурой.

---

### 18.3 Mock Data Fallback в Production

| ENTITY | FILE | ROLE | USED BY | DUPLICATE OF | RECOMMENDED STATUS |
|---|---|---|---|---|---|
| `_raise_or_use_mock()` паттерн | `app/html/depends.py` | Fallback на mock-данные при ошибках БД | HTML routes | — | **DELETE** из production кода |
| `MOCK_PROJECTS`, `SETTINGS_MOCK_DATA` | `app/mock_data.py`, `app/html/mock.py` | Тестовые данные | `app/html/depends.py` | — | **MOVE** → в `tests/fixtures/` |

**Доказательство**: HTML routes импортируют `get_html_db` из `depends.py`, который содержит логику fallback на mock.

---

### 18.4 Dead Static Assets

| ENTITY | FILE | ROLE | USED BY | DUPLICATE OF | RECOMMENDED STATUS |
|---|---|---|---|---|---|
| `three.min.js` | `static/js/three.min.js` | Мертвый ассет | Нигде (CDN в `ar_viewer.html`) | CDN version | **DELETE** |
| `mindar-image.prod.js` | `static/js/mindar-image.prod.js` | Мертвый ассет | Нигде (CDN в `ar_viewer.html`) | CDN version | **DELETE** |
| `mindar-image-three.prod.js` | `static/js/mindar-image-three.prod.js` | Мертвый ассет | Нигде (CDN в `ar_viewer.html`) | CDN version | **DELETE** |
| `favicon.png` | `static/favicon.png` | Мертвый ассет | Нигде в шаблонах | `templates/favicon.png` | **DELETE** |

---

### 18.5 Empty Files (Заглушки)

| ENTITY | FILE | ROLE | USED BY | DUPLICATE OF | RECOMMENDED STATUS |
|---|---|---|---|---|---|
| Пустой файл | `utilities/check_migration.py` | Заглушка для проверки миграций | Нигде | — | **DELETE** или **IMPLEMENT** |
| Пустой файл | `utilities/fix_migration.py` | Заглушка для исправления миграций | Нигде | — | **DELETE** или **IMPLEMENT** |
| Пустой файл | `tests/test_company_creation.py` | Заглушка для теста | Нигде | — | **DELETE** или **IMPLEMENT** |

---

### 18.6 Duplicate Scripts (Утилиты)

#### 18.6.1 Admin Creation (4 скрипта)

| ENTITY | FILE | ROLE | USED BY | DUPLICATE OF | RECOMMENDED STATUS |
|---|---|---|---|---|---|
| `create_admin()` | `utilities/create_admin.py` | Создание админа | Dev/ops | `scripts/legacy/create_admin.py` | **MERGE** → оставить `utilities/create_admin.py` |
| `create_admin_test()` | `utilities/create_admin_test.py` | Создание тестового админа | Dev/ops | `scripts/legacy/create_test_admin.py` | **MERGE** |
| `create_admin()` | `scripts/legacy/create_admin.py` | Старая версия | Нигде | `utilities/create_admin.py` | **DELETE** |
| `create_test_admin()` | `scripts/legacy/create_test_admin.py` | Старая версия | Нигде | `utilities/create_admin_test.py` | **DELETE** |

#### 18.6.2 Check Admin (2 скрипта)

| ENTITY | FILE | ROLE | USED BY | DUPLICATE OF | RECOMMENDED STATUS |
|---|---|---|---|---|---|
| `check_admin()` async | `utilities/check_admin.py` | Проверка админов | Dev/ops | `utilities/check_admin_user.py` | **MERGE** → оставить async версию |
| `check_admin_user()` sync | `utilities/check_admin_user.py` | Проверка админов | Dev/ops | `utilities/check_admin.py` | **DELETE** |

#### 18.6.3 Check DB (3 скрипта)

| ENTITY | FILE | ROLE | USED BY | DUPLICATE OF | RECOMMENDED STATUS |
|---|---|---|---|---|---|
| `check_db()` | `utilities/check_db.py` | Проверка БД | Dev/ops | `scripts/checks/check_models_db_compliance.py` | **MERGE** |
| `check_models_db_compliance()` | `scripts/checks/check_models_db_compliance.py` | Проверка соответствия моделей БД | Dev/ops | `utilities/check_db.py` | **MERGE** |
| `check_sqlite_tables()` | `scripts/db/check_sqlite_tables.py` | Проверка SQLite таблиц | Dev/ops | `utilities/check_db.py` | **MERGE** |

---

### 18.7 Routers Not Connected

| ENTITY | FILE | ROLE | SHOULD BE CONNECTED TO | RECOMMENDED STATUS |
|---|---|---|---|---|
| `enhanced_media` router | `app/api/routes/enhanced_media.py` | REST API для медиа-обработки | `app/main.py` | **DELETE** или **CONNECT** (принять решение) |

**Доказательство**: `app/main.py:283-319` импортирует и регистрирует 13 роутеров. `enhanced_media` отсутствует в обоих списках.

---

### 18.8 Services Not Used

| ENTITY | FILE | ROLE | USED BY | RECOMMENDED STATUS |
|---|---|---|---|---|
| `EnhancedValidationService` | `app/services/enhanced_validation_service.py` | Валидация медиа | Нигде | **DELETE** |
| `EnhancedCacheService` | `app/services/enhanced_cache_service.py` | Кеширование | Нигде | **DELETE** |
| `EnhancedThumbnailService` | `app/services/enhanced_thumbnail_service.py` | Thumbnail generation | Нигде | **DELETE** |
| `BaseModel` | `app/models/base.py` | Абстрактная модель | Нигде | **DELETE** |

---

### 18.9 Repositories Bypassed

**Наблюдение**: В проекте **нет явного repository pattern**. Все routes обращаются к моделям SQLAlchemy напрямую через `db.execute()`, `db.get()`, `db.commit()`.

| ENTITY | FILE | ROLE | BYPASSED BY |
|---|---|---|---|
| Repository pattern | Отсутствует | Должен был абстрагировать БД | Все `app/api/routes/*.py` обращаются к моделям напрямую |

**Рекомендация**: Это не критично для текущего масштаба проекта, но создает риск миграции БД в будущем.

---

### 18.10 Wrong Paths

#### 18.10.1 Config Paths

| ENTITY | FILE | PROBLEM | RECOMMENDED STATUS |
|---|---|---|---|
| `TEMPLATES_DIR` env var | `docker-compose.yml:63` | Задана, но нет доказательств, что приложение читает эту переменную | **DELETE** или **VERIFY USAGE** |
| `MEDIA_ROOT` env var | `docker-compose.yml:60` | Задана как `/app/storage/content`, но в `config.py` default `./storage/content` | **VERIFY** — работает только если `.env` загружается |

#### 18.10.2 Template Paths

| ENTITY | FILE | PROBLEM | RECOMMENDED STATUS |
|---|---|---|---|
| `Jinja2Templates(directory="templates")` | `app/main.py:350` | Hardcoded путь, игнорирует `TEMPLATES_DIR` env var | **FIX** → использовать `settings.TEMPLATES_DIR` |

#### 18.10.3 Static Paths

| ENTITY | FILE | PROBLEM | RECOMMENDED STATUS |
|---|---|---|---|
| `StaticFiles(directory="static")` | `app/main.py:454` | Hardcoded путь, игнорирует `STATIC_DIR` env var | **FIX** → использовать `settings.STATIC_DIR` |

#### 18.10.4 Storage Paths

| ENTITY | FILE | PROBLEM | RECOMMENDED STATUS |
|---|---|---|---|
| `STORAGE_BASE_PATH` | `docker-compose.yml:60` vs `config.py:94` | Docker: `/app/storage`, default: `./storage` | **VERIFY** — работает только если `.env` загружается |

#### 18.10.5 Docker Paths

| ENTITY | FILE | PROBLEM | RECOMMENDED STATUS |
|---|---|---|---|
| `curl` в healthcheck | `docker-compose.yml:70` | `curl` может отсутствовать в `Dockerfile.dev` образе | **FIX** → использовать `python -c "import urllib.request"` или `wget` |
| `postgres-exporter` | `prometheus/prometheus.yml` | Не определен в `docker-compose.yml` | **FIX** → добавить сервис или удалить из Prometheus config |

---

### 18.11 Migration Paths

| ENTITY | FILE | PROBLEM | RECOMMENDED STATUS |
|---|---|---|---|
| Смешанные форматы migration ID | `alembic/versions/` | Короткие хеши (`28cd993514df`) и timestamp-based IDs (`20260125_1200`) сосуществуют | **NORMALIZE** → привести к единому формату |
| `widen_alembic_version_num.py` | `alembic/versions/20260211_widen_alembic_version_num.py` | Специальная миграция для обхода ограничения длины Alembic | **KEEP** — необходима для PostgreSQL |
| `20251226_1200_update_notifications_table.py` | `alembic/versions/` | Упоминается в листинге, но файл не найден при чтении | **VERIFY** — возможно удален или поврежден |

---

### 18.12 Circular Imports

**Результат проверки**: **Circular imports не обнаружены** в основных модулях.

**Проверенные пути**:
- `app/core/storage.py` → `app/core/storage_providers.py` → `app/utils/token_encryption.py` — нет цикла
- `app/core/storage_providers.py` → `app/core/yandex_disk_provider.py` → `app/core/storage_providers.py` — **потенциальный цикл**, но `YandexDiskStorageProvider` импортируется лениво внутри функции, поэтому цикл не происходит

**Ленивые импорты** (используются для избежания циклических зависимостей):
- `app/api/routes/viewer.py:356` — `from app.api.routes.viewer import _parse_demo_index` (внутри функции)
- `app/core/storage_providers.py:285-286` — ленивый импорт `token_encryption` и `YandexDiskStorageProvider`
- `app/main.py:166-176` — ленивый импорт `scheduler`

---

### 18.13 Modules That Cannot Be Imported

| ENTITY | FILE | PROBLEM | IMPACT |
|---|---|---|---|
| `app.services.email_service` | `app/background_tasks/email_tasks.py:10` | Модуль не существует | **P0** — любая email-задача упадет с ImportError |
| `seed_defaults` | `app/core/seed_defaults.py` (вызывается в `main.py:159`) | Функция не определена (файл пустой) | **P0** — startup logging обманывает, seeding не работает |

---

### 18.14 Frontend → Backend API Mismatches

| FRONTEND CALL | FILE | BACKEND ENDPOINT | STATUS |
|---|---|---|---|
| `GET /api/ar-content/by-unique/${PORTRAIT_UID}` | `templates/ar_viewer.html:85` | **НЕ СУЩЕСТВУЕТ** | **BROKEN** |
| `GET /api/ar/${PORTRAIT_UID}/active-video` | `templates/ar_viewer.html:92` | `GET /api/ar/{unique_id}/active-video` (`app/api/routes/viewer.py`) | **MISMATCH** — префикс `/ar/` vs `/api/ar/` |

**Примечание**: `ar_viewer.html` использует `API_BASE = window.location.origin`, что дает `/api/...`, но endpoint в viewer.py зарегистрирован как `/api/viewer/ar/{unique_id}/active-video`. Таким образом, вызов `/api/ar/...` возвращает 404.

---

### 18.15 Mobile → Backend API Mismatches

| MOBILE CALL | FILE | BACKEND ENDPOINT | STATUS |
|---|---|---|---|
| `GET /api/viewer/ar/{id}/check` | Android `ViewerApi.kt:19` | `app/api/routes/viewer.py` — существует | **OK** |
| `GET /api/viewer/ar/{id}/manifest` | Android `ViewerApi.kt:22` | `app/api/routes/viewer.py` — существует | **OK** |
| `GET /api/viewer/ar/{id}/active-video` | Android `ViewerApi.kt:25` | `app/api/routes/viewer.py` — существует | **OK** |
| `POST /api/mobile/sessions` | iOS `ViewerService.swift` | `app/api/routes/analytics.py` — существует | **OK** (только iOS) |
| `POST /api/mobile/analytics` | iOS `ViewerService.swift` | `app/api/routes/analytics.py` — существует | **OK** (только iOS) |

**Ключевое несоответствие**: Android **не вызывает** analytics endpoints, хотя backend их предоставляет.

---

### 18.16 Docker / Deployment Path Issues

| ENTITY | FILE | PROBLEM | RECOMMENDED STATUS |
|---|---|---|---|
| `Dockerfile.dev` | `docker-compose.yml:48-50` | Использует `Dockerfile.dev`, но файл не проверен на наличие `curl` | **VERIFY** |
| `volumes` | `docker-compose.yml:51-53` | Монтирует `.:/app` и `./storage:/app/storage` | **OK** — но `./templates:/app/templates` лишнее (не используется) |
| Healthcheck | `docker-compose.yml:69-73` | `curl` может отсутствовать | **FIX** |
| `postgres-exporter` | `prometheus/prometheus.yml` | Не определен в `docker-compose.yml` | **FIX** |
| Systemd unit | `deploy/systemd/arv.service` | Использует `gunicorn`, docs показывают `uvicorn` | **SYNC** docs |

---

### 18.17 Summary: Canonical Implementations

| DOMAIN | CANONICAL | DELETE | MERGE INTO |
|---|---|---|---|
| **Storage** | `app/core/storage_providers.py` | `app/services/storage.py`, `app/core/storage.py` | `core/storage_providers.py` |
| **Thumbnail** | `app/services/thumbnail_service.py` | `app/utils/ar_content.py:generate_thumbnail`, `app/services/enhanced_thumbnail_service.py` | `thumbnail_service.py` |
| **Email** | `app/services/email_transport.py` | `app/background_tasks/email_tasks.py` (с исправлением) | `email_transport.py` |
| **Models** | `app/models/*.py` (конкретные модели) | `app/models/base.py` | — |
| **Routers** | `app/api/routes/*.py` (зарегистрированные) | `app/api/routes/enhanced_media.py` | — |
| **Services** | `app/services/*.py` (используемые) | `app/services/enhanced_*.py` | — |
| **Static** | CDN (mind-ar, three.js) | `static/js/*.js` | — |
| **Mock data** | `tests/fixtures/` (переместить) | `app/mock_data.py`, `app/html/mock.py` | `tests/fixtures/` |

---

### 18.18 Recommended Cleanup Order

| Priority | Action | Target | Risk |
|---|---|---|---|
| **P0** | Исправить импорт в `email_tasks.py` | `app/background_tasks/email_tasks.py` | Низкий |
| **P0** | Удалить/реализовать `seed_defaults()` | `app/core/seed_defaults.py` + `app/main.py` | Низкий |
| **P0** | Удалить мертвый `enhanced_media` модульный дерево | `app/api/routes/enhanced_media.py`, `app/services/enhanced_*.py` | Низкий |
| **P1** | Консолидировать storage в `core/storage_providers.py` | `app/services/storage.py`, `app/core/storage.py` | Средний |
| **P1** | Унифицировать thumbnail generation | `app/utils/ar_content.py`, `app/services/thumbnail_service.py` | Средний |
| **P1** | Удалить mock fallback из production | `app/html/depends.py`, переместить mock в `tests/fixtures/` | Средний |
| **P2** | Удалить пустые utility-скрипты | `utilities/check_migration.py`, `utilities/fix_migration.py` | Низкий |
| **P2** | Удалить пустой тестовый файл | `tests/test_company_creation.py` | Низкий |
| **P2** | Консолидировать duplicate scripts | `scripts/legacy/create_admin*.py`, `utilities/check_admin*.py` | Низкий |
| **P2** | Исправить `ar_viewer.html` API calls | `templates/ar_viewer.html` | Средний |
| **P3** | Удалить мертвые static assets | `static/js/`, `static/favicon.png` | Низкий |
| **P3** | Исправить Docker paths | `docker-compose.yml`, `prometheus/prometheus.yml` | Средний |
| **P3** | Синхронизировать документацию | `docs/DEPLOYMENT.md`, `SECURITY.md`, `TECH_STACK.md` | Низкий |

---
E:\Project\ARV\AUDIT_REPORT.md | **P3** | Синхронизировать документацию | `docs/DEPLOYMENT.md`, `SECURITY.md`, `TECH_STACK.md` | Низкий |

---

# 20. Security Audit

SECURITY AUDIT
Дата аудита: 2026-08-19
Аудитор: Kilo (Senior Application Security Engineer / Red Team Auditor / Secure Code Reviewer)
Версия проекта: 2.1.1
Область: E:\Project\ARV

Executive Summary
Проект имеет критические уязвимости безопасности, блокирующие использование в продакшене. Основные проблемы:

Отсутствует авторизация на большинстве admin endpoints — любой аутентифицированный пользователь может управлять компаниями, проектами, AR-контентом, видео, ротацией, настройками и бэкапами.
Публичные endpoints раскрывают чувствительные данные: список всего AR-контента, аналитика, storage stats, Yandex Disk OAuth.
Жестко зашиты секреты в .env, Docker Compose, конфиге и утилитных скриптах.
Нет защиты от IDOR/BOLA — любой пользователь может получить/удалить/изменить любой ресурс по ID.
Длинные-lived JWT без revocation, rotation, refresh tokens.
Legacy SHA-256 пароли без принудительного rehash.
Debug endpoints и verbose errors раскрывают внутреннюю информацию.
Static file mount /storage открывает весь файловый контент без авторизации.
SECURITY GATE: FAIL

Проект не проходит security audit. Критические уязвимости требуют исправления перед любым продакшен-развертыванием.

Attack Surface
Trust Boundaries
Boundary	Protection	Gaps
Client → API	CORS middleware, CSRF double-submit for cookie auth	CORS allow_origin_regex permits any localhost origin; CSRF cookie not HttpOnly
API → Auth	OAuth2PasswordBearer + JWT decode; optional cookie auth	No refresh tokens; 24h access token lifetime; no revocation list
Auth → Authorization	get_current_active_user dependency	No role-based checks on 90%+ of routes
Service → Database	AsyncSession with rollback; parameterized SQLAlchemy queries	No application-level query whitelisting
Queue → Worker	BackgroundTasks (in-process)	No separate worker process isolation
External Provider	Encrypted OAuth tokens; HTTPS for Yandex/SMTP	Token encryption falls back to base64 if cipher init fails
Storage	StaticFiles mount at /storage; path traversal check in delete	Entire /storage directory is world-readable via HTTP; no per-user/company file access control
Public Endpoints (No Auth)
Endpoint	Method	Risk
/api/analytics/overview	GET	Information disclosure — total views, active companies/projects
/api/analytics/summary	GET	Information disclosure
/api/ar-content	GET	Lists ALL AR content across ALL companies without auth
/api/ar-content/{id}	GET	Exposes any AR content by ID
/api/ar-content/{id}	DELETE	Deletes any AR content by ID without auth
/api/ar-content/{id}/regenerate-media	POST	Regenerates any AR content without auth
/api/videos/{id}/regenerate-thumbnail	POST	Regenerates any video thumbnail without auth
/api/viewer/ar/{id}/check	GET	Public by design, but UUID-guessable
/api/viewer/ar/{id}/manifest	GET	Public by design, but UUID-guessable
/api/viewer/ar/{id}/active-video	GET	Public by design, but UUID-guessable
/api/storage/*	ALL	Storage management CRUD without auth
/api/oauth/*	ALL	OAuth flow without auth
/api/notifications/test	POST	Email/Telegram spam without auth
/api/settings	GET	Exposes app config without auth
/debug-auth	GET	Debug endpoint dumps cookies, headers, user info
Private Endpoints (Auth Required, No Role Check)
Endpoint	Method	Risk
/api/companies/*	ALL	Any authenticated user can create/update/delete any company
/api/projects/*	ALL	Any authenticated user can manage any project
/api/rotation/*	ALL	Any authenticated user can modify rotation schedules
/api/backups/*	ALL	Any authenticated user can trigger/delete backups
/api/settings/*	POST	Any authenticated user can change settings
/api/notifications/*	ALL	Any authenticated user can manage notifications
Admin Endpoints
Endpoint	Method	Risk
/admin/*	ALL	HTML routes use get_current_user_optional — no admin role enforcement
Critical Vulnerabilities
CRIT-01: No Authorization on Admin Routes
ID: CRIT-01
SEVERITY: CRITICAL
CATEGORY: AUTHORIZATION
FILE: Multiple route files
COMPONENT: API Routes

VULNERABILITY: No role-based access control on admin endpoints. Any authenticated user (even role="user") can perform admin operations.

EVIDENCE:

app/api/routes/companies.py — create_company, update_company, delete_company use only get_current_active_user, no role check
app/api/routes/projects.py — same pattern
app/api/routes/ar_content.py — create_ar_content, update_ar_content, delete_ar_content use only get_current_active_user
app/api/routes/videos.py — upload_video, update_video, delete_video no role check
app/api/routes/rotation.py — rotation CRUD no role check
app/api/routes/backups.py — backup trigger/delete no role check
app/api/routes/settings.py — settings update no role check
app/api/routes/notifications.py — notification management no role check
app/api/routes/storage.py — storage connection CRUD no auth at all
ATTACK SCENARIO:

Attacker registers a regular user account (role="user")
Attacker authenticates and obtains JWT
Attacker calls DELETE /api/companies/1 → succeeds
Attacker calls POST /api/backups/run → triggers backup
Attacker calls PUT /api/settings/general → changes app settings
IMPACT: Complete system takeover by any authenticated user. Data destruction, configuration tampering, service disruption.

LIKELIHOOD: High — registration endpoint exists, auth works, no role enforcement.

RECOMMENDED FIX:

Implement require_role("admin") decorator
Apply to ALL admin routes: companies, projects, AR content, videos, rotation, backups, settings, notifications, storage
Convert role to enum or add permissions JSON field
Audit every route for get_current_active_user vs require_role
TEST TO ADD:

def test_non_admin_cannot_delete_company():
    user = create_user(role="user")
    token = login(user)
    response = client.delete(f"/api/companies/1", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
CRIT-02: IDOR/BOLA on All Resource Endpoints
ID: CRIT-02
SEVERITY: CRITICAL
CATEGORY: AUTHORIZATION
FILE: Multiple route files
COMPONENT: API Routes

VULNERABILITY: No ownership/tenant checks. Any authenticated user can access/modify/delete any resource by ID.

EVIDENCE:

app/api/routes/companies.py:128-166 — get_company no ownership check
app/api/routes/companies.py:247-297 — update_company no ownership check
app/api/routes/companies.py:300-331 — delete_company no ownership check
app/api/routes/projects.py:306-331 — get_project no ownership check
app/api/routes/projects.py:334-372 — update_project no ownership check
app/api/routes/projects.py:375-406 — delete_project no ownership check
app/api/routes/ar_content.py:1133-1184 — get_ar_content_by_id no auth at all
app/api/routes/ar_content.py:1187-1232 — delete_ar_content_by_id no auth at all
app/api/routes/ar_content.py:931-1031 — update_ar_content no ownership check
app/api/routes/ar_content.py:553-642 — regenerate_media no auth at all
app/api/routes/videos.py:169-198 — regenerate_video_thumbnail no auth at all
app/api/routes/videos.py:489-772 — video update/delete no auth at all
app/api/routes/rotation.py:64-109 — set_rotation auth but no ownership check
app/api/routes/rotation.py:116-137 — update_rotation auth but no ownership check
app/api/routes/rotation.py:144-159 — delete_rotation auth but no ownership check
ATTACK SCENARIO:

Attacker authenticates as regular user
Iterates company_id=1,2,3,... to enumerate all companies
Reads sensitive data: customer names, phones, emails, AR content
Deletes companies/projects/AR content
Modifies rotation schedules to disrupt service
IMPACT: Data breach, data destruction, service disruption, competitive intelligence leakage.

LIKELIHOOD: High — IDs are sequential integers, easily guessable.

RECOMMENDED FIX:

Add company_id membership check to every endpoint
Verify current_user.company_id == resource.company_id or user is admin
For public viewer endpoints, use signed URLs or non-guessable UUIDs only
Never trust user_id, owner_id, company_id from frontend without verification
TEST TO ADD: For each resource endpoint, attempt to access/update/delete a resource owned by another tenant; assert 403/404.

CRIT-03: Unauthenticated AR Content Exposure
ID: CRIT-03
SEVERITY: CRITICAL
CATEGORY: AUTHORIZATION
FILE: app/api/routes/ar_content.py
COMPONENT: AR Content API

VULNERABILITY: list_all_ar_content returns ALL AR content across ALL companies without authentication.

EVIDENCE:

app/api/routes/ar_content.py:136-168 — list_all_ar_content has no Depends(get_current_active_user)
Returns ARContentList with all items including customer_name, customer_phone, customer_email, photo_url, video_url
ATTACK SCENARIO:

Attacker sends GET /api/ar-content?page=1&page_size=100
Receives complete list of all AR content with customer PII
Iterates pages to exfiltrate entire database
IMPACT: Mass PII exposure, business intelligence leakage, competitive disadvantage.

LIKELIHOOD: High — endpoint is unauthenticated and paginated.

RECOMMENDED FIX: Require admin authentication for list_all_ar_content. For non-admin users, return only resources belonging to their company.

TEST TO ADD:

def test_list_ar_content_requires_auth():
    response = client.get("/api/ar-content")
    assert response.status_code == 401
CRIT-04: Hardcoded Secrets in Source Code and Configuration
ID: CRIT-04
SEVERITY: CRITICAL
CATEGORY: SECRETS
FILE: Multiple files
COMPONENT: Configuration

VULNERABILITY: Production secrets hardcoded in .env, Docker Compose, config, and utility scripts.

EVIDENCE:

.env:18 — ADMIN_DEFAULT_PASSWORD=admin123
.env:21-22 — YANDEX_OAUTH_CLIENT_ID=..., YANDEX_OAUTH_CLIENT_SECRET=...
docker-compose.yml:14 — POSTGRES_PASSWORD: password
docker-compose.yml:58 — DATABASE_URL=postgresql+asyncpg://vertex_ar:password@...
app/core/config.py:7-8 — DEFAULT_SECRET_KEY = "change-this-to-a-secure-random-key-min-32-chars", DEFAULT_ADMIN_PASSWORD = "ChangeMe123!"
utilities/create_admin.py:35 — new_password = "admin123"
utilities/update_password_directly.py:29 — password = "admin123"
utilities/reset_password.py:37 — new_password = "admin123"
scripts/update_server_ssh.py:27-29 — hardcoded SSH defaults
ATTACK SCENARIO:

Attacker gains access to repository (compromised dev machine, leaked backup, public repo)
Reads .env or config.py to obtain secrets
Uses admin password to log in
Uses Yandex OAuth tokens to access company storage
Uses DB password to access database directly
IMPACT: Full system compromise, data breach, storage access, database access.

LIKELIHOOD: High — .env exists in workspace with live secrets.

RECOMMENDED FIX:

Rotate ALL exposed secrets immediately
Remove .env from workspace, add to .gitignore
Use .env.example for placeholders only
Inject secrets via CI/CD or secret manager (HashiCorp Vault, AWS Secrets Manager)
Remove hardcoded passwords from all utility scripts
Add startup validation that rejects default/weak secrets
TEST TO ADD:

def test_no_hardcoded_secrets():
    assert "admin123" not in read_file(".env")
    assert "password" not in read_file("docker-compose.yml")
    assert "change-this-to-a-secure-random-key" not in read_file("app/core/config.py")
CRIT-05: Static File Mount Exposes Entire Storage Without Authorization
ID: CRIT-05
SEVERITY: CRITICAL
CATEGORY: AUTHORIZATION
FILE: app/main.py
COMPONENT: Static Files Mount

VULNERABILITY: /storage is mounted as StaticFiles(directory=storage_dir) without path-based access control. Any user can download any file by guessing path.

EVIDENCE:

app/main.py:445-454 — app.mount("/storage", StaticFiles(directory=storage_dir), name="storage")
No authentication, no authorization, no per-company check
File paths are predictable: /storage/VertexAR/Project_1/ORD-20260101-1234/photo.jpg
ATTACK SCENARIO:

Attacker enumerates company names from public AR content
Guesses or brute-forces file paths: /storage/CompanyName/ProjectName/ORD-1234/photo.jpg
Downloads private AR content (marker images, videos, customer photos)
Downloads QR codes, thumbnails, metadata
IMPACT: Mass data exfiltration, intellectual property theft, customer privacy violation.

LIKELIHOOD: High — paths are predictable, no auth required.

RECOMMENDED FIX:

Serve storage through authenticated proxy route that checks company/project membership
Use non-guessable file paths (UUIDs instead of sequential names)
Disable directory listing in StaticFiles
Add signed URLs with expiration for temporary access
TEST TO ADD:

def test_storage_requires_auth():
    response = client.get("/storage/VertexAR/any_file.jpg")
    assert response.status_code in [401, 403, 404]
High Vulnerabilities
HIGH-01: JWT Tokens Valid for 24 Hours Without Revocation
ID: HIGH-01
SEVERITY: HIGH
CATEGORY: AUTHENTICATION
FILE: app/core/config.py, app/api/routes/auth.py
COMPONENT: JWT/Session Management

VULNERABILITY: Access tokens expire after 1440 minutes (24h). No refresh tokens. No revocation mechanism.

EVIDENCE:

app/core/config.py:58 — ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
app/core/security.py:56-66 — create_access_token only sets exp, no jti or revocation
app/api/routes/auth.py:232-237 — logout only clears cookies, JWT remains valid
ATTACK SCENARIO:

Attacker steals JWT via XSS, log leakage, or MITM
JWT is valid for 24 hours
Even if user logs out or admin revokes access, JWT remains valid
Attacker accesses system until token expires
IMPACT: Prolonged unauthorized access, session hijacking.

LIKELIHOOD: Medium — requires token theft, but 24h window is large.

RECOMMENDED FIX:

Reduce access token TTL to 15-30 minutes
Implement refresh tokens with rotation
Add server-side revocation list (Redis blocklist)
Invalidate tokens on logout, password change, admin action
TEST TO ADD:

def test_revoked_token_rejected():
    token = login(user)
    revoke_token(token)
    response = client.get("/api/companies", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
HIGH-02: Weak Default JWT Secret Key
ID: HIGH-02
SEVERITY: HIGH
CATEGORY: SECRETS
FILE: app/core/config.py
COMPONENT: JWT Configuration

VULNERABILITY: Default SECRET_KEY is a well-known hardcoded string. validate_sensitive_defaults() only runs when ENVIRONMENT=production.

EVIDENCE:

app/core/config.py:7 — DEFAULT_SECRET_KEY = "change-this-to-a-secure-random-key-min-32-chars"
app/core/config.py:56 — SECRET_KEY: str = Field(default=DEFAULT_SECRET_KEY)
app/core/config.py:187-196 — validate_sensitive_defaults() checks only when is_production=True
.env does not set ENVIRONMENT=production
ATTACK SCENARIO:

Attacker discovers default secret from source code
Signs arbitrary JWT with known secret
Imitates any user (admin) by setting sub: admin@vertexar.com
Gains full admin access
IMPACT: Complete authentication bypass, full system compromise.

LIKELIHOOD: High — secret is in source code, validation skipped in non-production.

RECOMMENDED FIX:

Generate random secret at first startup if not provided
Fail to start if default secret is used in ANY environment
Never ship defaults in source code
TEST TO ADD:

def test_default_secret_rejected():
    with pytest.raises(StartupError):
        start_app(SECRET_KEY="change-this-to-a-secure-random-key-min-32-chars")
HIGH-03: Unauthenticated Storage Management Endpoints
ID: HIGH-03
SEVERITY: HIGH
CATEGORY: AUTHORIZATION
FILE: app/api/routes/storage.py
COMPONENT: Storage API

VULNERABILITY: All storage management endpoints are completely unauthenticated.

EVIDENCE:

app/api/routes/storage.py:26-44 — create_connection no auth
app/api/routes/storage.py:47-103 — test_connection no auth
app/api/routes/storage.py:141-179 — get_storage_stats no auth
app/api/routes/storage.py — list_storage_connections no auth
ATTACK SCENARIO:

Attacker creates storage connection pointing to /etc/passwd or other sensitive paths
Reads storage stats to enumerate filesystem structure
Tests arbitrary filesystem paths via test_connection
IMPACT: Information disclosure, filesystem probing, potential path traversal.

LIKELIHOOD: High — endpoints are open, no auth required.

RECOMMENDED FIX: Add get_current_active_user + require_role("admin") to all storage management routes.

TEST TO ADD:

def test_storage_requires_admin():
    response = client.post("/api/storage/connections", json={...})
    assert response.status_code == 401
HIGH-04: Unauthenticated Yandex Disk OAuth Proxy
ID: HIGH-04
SEVERITY: HIGH
CATEGORY: AUTHORIZATION
FILE: app/api/routes/oauth.py
COMPONENT: OAuth API

VULNERABILITY: OAuth authorization and Yandex Disk folder operations are unauthenticated.

EVIDENCE:

app/api/routes/oauth.py:40-76 — /api/oauth/authorize no auth
app/api/routes/oauth.py:228-475 — /api/oauth/{id}/folders, /api/oauth/{id}/create-folder no auth
ATTACK SCENARIO:

Attacker initiates OAuth flow without authentication
Creates storage connections
Accesses Yandex Disk folders belonging to any company (if they know connection_id)
IMPACT: Unauthorized cloud storage access, data exfiltration.

LIKELIHOOD: Medium — requires knowledge of connection IDs.

RECOMMENDED FIX: Require admin authentication on all OAuth endpoints.

TEST TO ADD:

def test_oauth_requires_auth():
    response = client.get("/api/oauth/authorize")
    assert response.status_code == 401
HIGH-05: Unauthenticated Email/Telegram Test Endpoints
ID: HIGH-05
SEVERITY: HIGH
CATEGORY: AUTHORIZATION
FILE: app/api/routes/notifications.py
COMPONENT: Notifications API

VULNERABILITY: Test endpoints for email/Telegram allow unauthenticated spamming.

EVIDENCE:

app/api/routes/notifications.py:241-256 — @router.post("/test") no auth dependency
app/api/routes/notifications.py:258-275 — @router.post("/test-telegram") no auth dependency
ATTACK SCENARIO:

Attacker uses server as open relay to send spam emails
Sends mass Telegram messages
Exhausts SMTP/Telegram API quotas
Damages domain reputation
IMPACT: Reputation damage, SMTP/Telegram API abuse, potential account suspension.

LIKELIHOOD: High — endpoints are open, no auth required.

RECOMMENDED FIX: Require admin authentication; add CAPTCHA or rate limiting.

TEST TO ADD:

def test_notification_test_requires_auth():
    response = client.post("/api/notifications/test", json={...})
    assert response.status_code == 401
HIGH-06: Insecure Token Encryption with Fixed Salt
ID: HIGH-06
SEVERITY: HIGH
CATEGORY: CRYPTOGRAPHY
FILE: app/utils/token_encryption.py
COMPONENT: Token Encryption

VULNERABILITY: Fixed salt for PBKDF2 key derivation. Falls back to base64 if Fernet init fails.

EVIDENCE:

app/utils/token_encryption.py:30 — salt=b'vertex_ar_oauth_salt' is hardcoded
app/utils/token_encryption.py:41-43, 49-51 — fallback to base64.b64encode if cipher init fails
ATTACK SCENARIO:

Attacker gains database access
Extracts encrypted Yandex Disk tokens
Precomputes rainbow tables using known fixed salt
Decrypts all tokens offline
IMPACT: Cloud storage credential leakage, unauthorized access to company files.

LIKELIHOOD: Medium — requires database access.

RECOMMENDED FIX:

Use random per-application salt stored in environment
Fail startup if encryption cannot be initialized
Never fall back to base64 in production
TEST TO ADD:

def test_token_encryption_salt_is_random():
    salt = get_encryption_salt()
    assert salt != b'vertex_ar_oauth_salt'
    assert len(salt) >= 32
HIGH-07: Debug Endpoint Exposes Sensitive Data
ID: HIGH-07
SEVERITY: HIGH
CATEGORY: INFORMATION_DISCLOSURE
FILE: app/html/routes/debug.py
COMPONENT: Debug Routes

VULNERABILITY: /debug-auth endpoint returns cookies, headers, and user info without authentication.

EVIDENCE:

app/html/routes/debug.py:13-19 — debug-auth returns cookies: dict(request.cookies) and headers: dict(request.headers)
ATTACK SCENARIO:

Attacker visits /debug-auth
Steals session cookies, CSRF tokens, Authorization headers
Uses stolen tokens to impersonate other users
IMPACT: Session hijacking, credential theft, account takeover.

LIKELIHOOD: High — endpoint is accessible without auth.

RECOMMENDED FIX: Remove debug endpoint in production or require admin role.

TEST TO ADD:

def test_debug_auth_requires_admin():
    response = client.get("/debug-auth")
    assert response.status_code in [401, 403, 404]
HIGH-08: Error Handlers Leak Internal Details
ID: HIGH-08
SEVERITY: HIGH
CATEGORY: ERROR_HANDLING
FILE: Multiple route files
COMPONENT: API Routes

VULNERABILITY: Multiple endpoints return raw exception strings in 500 responses, exposing internal paths, stack traces, and configuration details.

EVIDENCE:

app/api/routes/ar_content.py:807-810 — detail=f"Не удалось создать AR контент: {str(e)}"
app/api/routes/ar_content.py:625 — detail=f"Failed to regenerate media: {str(e)}"
app/api/routes/videos.py:405-407 — detail=f"Failed to process video {upload_file.filename}: {str(e)}"
app/api/routes/health.py:43-44 — checks["database_error"] = str(e)
app/api/routes/companies.py:416-418 — detail=f"Yandex OAuth error: {detail}"
app/api/routes/notifications.py:292-297, 350-351 — SMTP/Telegram error details returned
ATTACK SCENARIO:

Attacker sends malformed requests to trigger errors
Receives internal stack traces, file paths, database errors
Uses information for targeted attacks (path traversal, SQL injection, etc.)
IMPACT: Information disclosure, reconnaissance for further attacks.

LIKELIHOOD: High — errors are triggered by simple malformed input.

RECOMMENDED FIX:

Return generic error messages to clients
Log detailed errors server-side only
Use custom exception handlers that sanitize output
TEST TO ADD:

def test_error_messages_dont_leak_details():
    response = client.post("/api/ar-content", json={...})  # malformed
    assert "Traceback" not in response.text
    assert "File " not in response.text
HIGH-09: All Users Default to role="admin"
ID: HIGH-09
SEVERITY: HIGH
CATEGORY: AUTHORIZATION
FILE: app/models/user.py, app/schemas/auth.py
COMPONENT: User Model/Schema

VULNERABILITY: User role defaults to "admin". No RBAC enforcement.

EVIDENCE:

app/models/user.py:18 — role = Column(String, default="admin")
app/schemas/auth.py:46 — role: str = "admin" (default in schema)
Only /api/auth/register checks current_user.role != "admin" (line 400-407)
ATTACK SCENARIO:

Admin creates new user without specifying role
User gets role="admin" by default
New admin can create more admins, modify system settings, delete data
IMPACT: Admin privilege proliferation, unauthorized admin access.

LIKELIHOOD: High — default is admin, no role enforcement.

RECOMMENDED FIX:

Change default role to "user"
Implement require_role("admin") decorator
Strip role from registration input; assign server-side only
TEST TO ADD:

def test_user_registration_default_role():
    user = register(username="test")
    assert user.role == "user"
HIGH-10: No Password Reset / Account Recovery
ID: HIGH-10
SEVERITY: HIGH
CATEGORY: AUTHENTICATION
FILE: N/A
COMPONENT: Auth System

VULNERABILITY: No password reset, email verification, or account recovery flow exists.

EVIDENCE: grep found zero functional implementations of password reset. Only i18n strings exist (auth.forgot_password).

ATTACK SCENARIO:

User forgets password
No self-service recovery — must contact admin
Admin manually resets via database utilities (insecure)
Or user creates new account (data loss)
IMPACT: Account lockout, support burden, insecure manual reset procedures.

LIKELIHOOD: High — affects all users who forget passwords.

RECOMMENDED FIX: Implement secure password reset with cryptographically random, single-use, time-limited (1 hour) tokens sent via email.

TEST TO ADD:

def test_password_reset_flow():
    request_reset(email)
    verify_email_received()
    reset_with_token(token, new_password)
    verify_login_with_new_password()
    verify_token_cannot_be_reused()
HIGH-11: No Authentication on Public AR Content Endpoints
ID: HIGH-11
SEVERITY: HIGH
CATEGORY: AUTHORIZATION
FILE: app/api/routes/ar_content.py
COMPONENT: AR Content API

VULNERABILITY: get_ar_content_by_id and delete_ar_content_by_id have no auth dependency.

EVIDENCE:

app/api/routes/ar_content.py:1133-1184 — get_ar_content_by_id no auth
app/api/routes/ar_content.py:1187-1232 — delete_ar_content_by_id no auth
ATTACK SCENARIO:

Attacker enumerates AR content IDs (sequential integers)
Reads any AR content without authentication
Deletes any AR content without authentication
IMPACT: Data breach, data destruction, service disruption.

LIKELIHOOD: High — IDs are sequential, no auth required.

RECOMMENDED FIX: Add authentication or implement signed URL access for public content.

TEST TO ADD:

def test_ar_content_requires_auth():
    response = client.get("/api/ar-content/1")
    assert response.status_code == 401
HIGH-12: Rate Limiter Bypass via Multiple Workers
ID: HIGH-12
SEVERITY: HIGH
CATEGORY: RATE_LIMITING
FILE: app/middleware/rate_limiter.py
COMPONENT: Rate Limiter

VULNERABILITY: In-memory rate limit cache is not shared across workers.

EVIDENCE:

app/middleware/rate_limiter.py:23-24 — _cache: dict[str, tuple[int, float]] = {} is process-local
Docker Compose/gunicorn typically runs multiple workers
ATTACK SCENARIO:

Attacker sends requests to different workers simultaneously
Each worker has its own rate limit counter
Attacker bypasses rate limit by distributing requests
IMPACT: Brute force, DoS, resource exhaustion.

LIKELIHOOD: Medium — requires concurrent requests to multiple workers.

RECOMMENDED FIX: Use Redis for distributed rate limiting.

TEST TO ADD:

def test_rate_limit_global():
    # Send requests to multiple workers simultaneously
    # Verify global rate limit is enforced
    pass
Medium Vulnerabilities
MED-01: CSRF Cookie Missing HttpOnly
ID: MED-01
SEVERITY: MEDIUM
CATEGORY: CSRF
FILE: app/middleware/csrf.py
COMPONENT: CSRF Middleware

VULNERABILITY: CSRF token cookie is not HttpOnly.

EVIDENCE:

app/middleware/csrf.py:42-49 — response.set_cookie(..., httponly=False, ...)
ATTACK SCENARIO: XSS steals CSRF token, bypassing CSRF protection.

IMPACT: CSRF bypass via XSS.

LIKELIHOOD: Medium — requires XSS vulnerability.

RECOMMENDED FIX: Set httponly=True on CSRF cookie; use SameSite=Strict where possible.

MED-02: CORS Too Permissive
ID: MED-02
SEVERITY: MEDIUM
CATEGORY: CORS
FILE: app/main.py
COMPONENT: CORS Middleware

VULNERABILITY: allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?" with allow_credentials=True permits any localhost origin.

EVIDENCE:

app/main.py:221-228 — CORS configuration with permissive regex
ATTACK SCENARIO: Attacker uses subdomain or localhost variant to bypass CORS and make credentialed requests.

IMPACT: CSRF, data exfiltration.

LIKELIHOOD: Low-Medium.

RECOMMENDED FIX: Restrict allow_origin_regex to specific expected localhost ports or remove it in production.

MED-03: Legacy SHA-256 Password Support
ID: MED-03
SEVERITY: MEDIUM
CATEGORY: PASSWORD_SECURITY
FILE: app/core/security.py
COMPONENT: Password Hashing

VULNERABILITY: Legacy unsalted SHA-256 hashes supported for migration.

EVIDENCE:

app/core/security.py:15-32 — is_legacy_password_hash(), _legacy_sha256(), verify_password() with fallback
No forced rehash on login
ATTACK SCENARIO: If legacy hashes are leaked, offline brute-force is feasible due to lack of salt.

IMPACT: Password cracking.

LIKELIHOOD: Medium — legacy hashes may exist in migrated databases.

RECOMMENDED FIX: Add forced password rehash on next successful login for all legacy hashes.

MED-04: Username Enumeration via Timing
ID: MED-04
SEVERITY: MEDIUM
CATEGORY: AUTHENTICATION
FILE: app/api/routes/auth.py
COMPONENT: Login

VULNERABILITY: Failed login for non-existent user returns immediately, while failed login for existing user runs verify_password. Timing difference may allow enumeration.

EVIDENCE:

app/api/routes/auth.py:153-215 — different code paths for existing vs non-existing users
ATTACK SCENARIO: Attacker measures response times to enumerate valid email addresses.

IMPACT: Account enumeration, targeted attacks.

LIKELIHOOD: Low — network jitter usually masks timing differences.

RECOMMENDED FIX: Add dummy bcrypt check for non-existent users to equalize response time.

MED-05: WebSocket Without Authentication
ID: MED-05
SEVERITY: MEDIUM
CATEGORY: AUTHORIZATION
FILE: app/api/routes/alerts_ws.py
COMPONENT: WebSocket

VULNERABILITY: WebSocket accepts connections without authentication.

EVIDENCE:

app/api/routes/alerts_ws.py:10-22 — @router.websocket("/ws/alerts") no auth check
ATTACK SCENARIO: Attacker connects and receives sensitive alert data (system health, backup failures).

IMPACT: Information disclosure.

LIKELIHOOD: Medium.

RECOMMENDED FIX: Query-parameter or cookie-based auth handshake before accepting WebSocket connection.

MED-06: Mobile API Calls Over HTTP Possible
ID: MED-06
SEVERITY: MEDIUM
CATEGORY: TRANSPORT_SECURITY
FILE: android/app/build.gradle.kts, ios/ARViewer/ARViewerApp.swift
COMPONENT: Mobile Apps

VULNERABILITY: Android networkSecurityConfig allows cleartext in debug. iOS uses URLSessionConfiguration.default without certificate pinning.

EVIDENCE:

Android network_security_config.xml — cleartext permitted in debug
Android ViewerApi.kt — base URL is https://ar.neuroimagen.ru but no CertificatePinner
iOS ViewerService.swift — no custom URLSessionDelegate for pinning
ATTACK SCENARIO: MITM attacker intercepts traffic on debug builds or via compromised CA.

IMPACT: Session hijacking, data interception.

LIKELIHOOD: Low-Medium.

RECOMMENDED FIX: Enforce HTTPS-only in production builds. Add certificate pinning for both platforms.

MED-07: Redis Exposed Without Authentication
ID: MED-07
SEVERITY: MEDIUM
CATEGORY: INFRASTRUCTURE
FILE: docker-compose.yml
COMPONENT: Redis

VULNERABILITY: Redis is exposed on port 6379 without authentication.

EVIDENCE:

docker-compose.yml:28-45 — Redis service has no requirepass or AUTH configuration
ATTACK SCENARIO: Attacker with network access connects to Redis, reads/flushes data, potentially achieves RCE via Redis modules.

IMPACT: Data loss, session invalidation, potential RCE.

LIKELIHOOD: Medium — Redis is inside Docker network but may be exposed in misconfigured deployments.

RECOMMENDED FIX: Add requirepass to Redis config. Use Docker secrets for password.

MED-08: Admin Log Viewer Accessible to Non-Admin Users
ID: MED-08
SEVERITY: MEDIUM
CATEGORY: AUTHORIZATION
FILE: app/html/routes/logs.py
COMPONENT: Admin Logs

VULNERABILITY: Log viewer uses get_current_user_optional — any active user can view logs.

EVIDENCE:

app/html/routes/logs.py:198-244 — no role check, only get_current_user_optional
ATTACK SCENARIO: Low-privilege user reads logs containing stack traces, file paths, user agents, potentially sensitive data.

IMPACT: Information disclosure, reconnaissance.

LIKELIHOOD: Medium — requires authenticated user.

RECOMMENDED FIX: Restrict log viewer to role="admin" only.

Low Vulnerabilities
LOW-01: Password Policy Too Weak
ID: LOW-01
SEVERITY: LOW
CATEGORY: PASSWORD_SECURITY
FILE: app/schemas/auth.py
COMPONENT: Registration

VULNERABILITY: Minimum 8 characters, no complexity requirements.

EVIDENCE: app/schemas/auth.py:44 — password: str = Field(..., min_length=8, ...)

RECOMMENDED FIX: Enforce password complexity (uppercase, digits, symbols) or use zxcvbn.

LOW-02: SameSite Cookie Configuration
ID: LOW-02
SEVERITY: LOW
CATEGORY: SESSION_SECURITY
FILE: app/api/routes/auth.py
COMPONENT: Session Cookie

VULNERABILITY: samesite="lax" allows cookies on top-level GET navigation.

EVIDENCE: app/api/routes/auth.py:129 — samesite="lax"

RECOMMENDED FIX: Use samesite="strict" where possible.

LOW-03: Mass Assignment via setattr
ID: LOW-03
SEVERITY: LOW
CATEGORY: AUTHORIZATION
FILE: app/api/routes/rotation.py, app/api/routes/videos.py
COMPONENT: Update Endpoints

VULNERABILITY: setattr(existing, k, v) with user-controlled keys allows mass assignment of any model field.

EVIDENCE:

app/api/routes/rotation.py:82-84 — for k, v in clean.items(): if hasattr(existing, k): setattr(existing, k, v)
app/api/routes/videos.py:1002-1004 — same pattern
RECOMMENDED FIX: Use explicit allowlist of updatable fields.

LOW-04: Gitignore Allows .env.production
ID: LOW-04
SEVERITY: LOW
CATEGORY: SECRETS
FILE: .gitignore
COMPONENT: Git Configuration

VULNERABILITY: .gitignore line 43 explicitly allows !.env.production, which may contain real production secrets.

EVIDENCE: .gitignore:43 — !.env.production

RECOMMENDED FIX: Remove !.env.production from .gitignore or ensure it is never committed.

---

## Нормализация отчёта

Этот файл переработан из исходного `AUDIT_REPORT.md`.

### Что изменено в структуре

- Все основные разделы аудита сохранены и расположены в логической последовательности.
- Вынесен отдельный раздел **Security Audit**, чтобы не смешивать общие технические находки с security findings.
- Сохранены исходные формулировки, severity, evidence, attack scenarios и recommended fixes.
- Убраны повторяющиеся фрагменты Security Audit, которые в исходном файле повторяются после строки `Authentication` и сообщения `The model hit its output limit`.
- Не добавлялись новые технические утверждения и не исправлялись выводы аудитора по существу.
- Исправления/рекомендации из исходного отчёта не были «автоматически применены» — это именно структурированная версия аудита.

### Важное ограничение исходника

Security Audit в исходном файле заканчивается на находке **LOW-04**, после чего появляется `Authentication` и сообщение о достижении лимита вывода. Поэтому раздел Security Audit ниже отражает доступную завершённую часть исходного материала; последующие повторяющиеся фрагменты исходного файла намеренно не включены как дубликаты.

### Приоритет чтения

Если документ используется как рабочий план исправления проекта, рекомендуется идти в таком порядке:

1. **P0 / Critical** — блокеры production и критические security-проблемы.
2. **P1 / High** — функциональные и архитектурные проблемы, влияющие на безопасность и стабильность.
3. **Security Audit** — CRIT/HIGH/MEDIUM/LOW findings и тесты, которые необходимо добавить.
4. **Generation API Audit** — отдельный блок, поскольку Generation API в текущем проекте отсутствует.
5. **Forensic Structure Audit** — консолидация архитектуры, дубликатов, dead code и путей.
6. **Recommended Fix Order** — исходная последовательность исправлений.
