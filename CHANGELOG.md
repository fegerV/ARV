# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

Крупная работа по надёжности бэкапов и восстановлению (2026-08-20 … 2026-09-16).

### Added
- **Восстановление одной командой**: `deploy/backup/recover.sh --backup-id N --target-db X`,
  с `--cutover` и автооткатом при неудаче. Ручные шаги остались как запасной путь.
- **`restore --from-file <артефакт>`** — восстановление, когда БД потеряна полностью:
  не читает БД вообще (токен хранилища лежит в самой БД), нужен только файл.
- **`verify --from-file` / `drill --from-file`** — проверка и пробное восстановление
  на любой машине, где есть `age`; ключ не обязательно монтировать на прод.
  `--record-as <id>` закрывает алерт, записывая результат в `backup_history`.
- **Скачивание артефакта вручную**: `backup download` и кнопка в админке.
- **Бэкап медиа** (`restic`, ежедневно 03:30) и **архив секретов** (`tar` + `age`, вс 04:00).
- **Шифрование дампов** (`age`, X25519); приватный ключ хранится **вне** сервера.
- **GFS-лестница хранения** 7 ежедневных / 4 недельных / 12 месячных / 3 годовых
  (`app/services/backup_rotation.py`) — даёт точку восстановления месячной давности,
  чего правило «N новейших копий» не умело.
- **CLI** `app/cli/backup.py`: `status`, `run`, `list`, `download`, `verify`, `drill`, `restore`.
- **Метрики и алерты** Prometheus по бэкапам (`backup_metrics.py`, `prometheus/alert.rules.yml`).
- **Юниты и таймеры** systemd: медиа, секреты, verify, drill.

### Changed
- **Админка теперь управляет тем, что действует.** Вкладка «Бэкапы» выводит четыре поля
  GFS-лестницы; ранее она показывала `backup_retention_days` / `backup_max_copies`,
  которые ротация игнорирует, а саму лестницу изменить через интерфейс было нельзя.
- **Планировщик сериализован между процессами** общим `flock` на `/var/lock/arv-db.lock`
  (тот же файл, что и в `deploy/backup/backup-db.sh`), поэтому число воркеров gunicorn
  больше не влияет на число бэкапов.
- Тесты запускаются герметично через `scripts/run_tests.sh` (подгружает `.env.test`),
  а не наследуют боевой `.env`.

### Fixed
- **Восстановление не работало вообще**: `download_backup()` вызывал `save_file()`
  (метод загрузки) вместо `get_file()` → `FileNotFoundError` в `verify`, `drill`, `restore`.
- **Дамп не восстанавливался** без `--no-owner`.
- **Дублирование бэкапа между воркерами**: два процесса gunicorn считали одно имя артефакта,
  загружали в один ключ, писали две строки истории, а ротация удаляла файл вместе со строкой —
  оставалась запись `status=success` на несуществующий артефакт (404). Исправлено локом
  и микросекундной точностью имени.
- **`verify`/`drill` больше не «кричат волком»**, когда дамп зашифрован, а ключа на проде нет:
  честно сообщают `skipped` / `no_identity` вместо ложного провала.
- Задача бэкапа секретов падала и светила `SECRET_KEY` в логах.
- `JobLock` стал fail-safe: недоступность лок-файла больше не блокирует бэкап навсегда.
- Шаблонизация на современном Starlette; 24 устаревших теста починены.
- Тесты больше не пишут в рабочее дерево и не хардкодят диск `E:`.

### Security
- Устранены находки аудита **ARV-001 … ARV-039**: IDOR/BOLA, обход CSRF-исключений,
  отсутствие tenant-scope в списках и формах (компании, проекты, AR-контент, хранилище,
  дашборд, аналитика), утечка ростера компаний.
- Удалён `/debug/storage-test`, светивший пути файловой системы в продакшене.
- Удалён утёкший `/tmp/ARV_deploy.tar.gz` (305 МБ, режим `0644`, содержал `.env` и TLS-ключ).
  ⚠️ Ротация затронутых секретов — отдельная задача, порядок описан в `docs/RESTORE_RUNBOOK.md`.

## [2.2.0] - 2026-08-19

### Security
- **IDOR/BOLA Protection**: Added `company_id` to `User` model and `user_id` to `Notification` model
- **Authorization dependencies**: Created `require_company_access`, `require_resource_access` in `app/api/deps_authz.py`
- **Ownership checks**: Applied company-based access control to all protected endpoints (companies, projects, ar_content, videos, notifications, storage, analytics, backups, rotation, oauth, settings)
- **List endpoint filtering**: All list endpoints now filter by user's company_id; super-admins bypass filter
- **Super-admin support**: `is_super_admin` flag for full access across companies
- **Test coverage**: Added `tests/test_idor_security.py` with 12 security tests

### Changed
- `seed_defaults()` now assigns `company_id` and `is_super_admin=True` to default admin
- Protected route handlers now require `current_user` and sometimes `company` dependencies

## [2.1.0] - 2026-02-15

### Added
- **Database Backup System**: automated PostgreSQL backups to Yandex Disk
  - `BackupService` — pg_dump → gzip → upload to YD → rotation
  - `APScheduler` integration — cron-based scheduling (daily / 12h / weekly / custom)
  - Backup history model (`backup_history` table) with status tracking
  - API endpoints: `POST /api/backups/run`, `GET /history`, `GET /status`, `DELETE /{id}`
  - Admin UI: new "Бэкапы" tab in Settings with configuration form, manual trigger, history table
  - Automatic rotation by retention days and max copies
- **Yandex Disk Storage Provider**: upload/download/proxy for company files via YD API
  - Per-company storage provider selection (local / yandex_disk)
  - HTTP Range header proxy for video seeking from YD
  - Video upload to YD with automatic thumbnail generation
- **Multi-size WebP Thumbnails**: video thumbnails in 3 sizes (150×112, 320×240, 640×480)
- **Video Management**: upload additional videos, delete videos, regenerate thumbnails
- **Lightbox Improvements**: high-res portrait photos, video player in lightbox

### Changed
- Settings page: added "Бэкапы" tab alongside general, security, AR
- `AllSettings` schema now includes `BackupSettings`
- `SettingsService` extended with `update_backup_settings()`
- Application lifespan now starts/stops APScheduler

### Fixed
- **Dashboard crash** (`dashboard_data_error`): datetime naive/aware mismatch when querying `ar_view_sessions` — switched to `datetime.utcnow()` for naive column compatibility
- **Project update crash**: undefined `description` variable in `projects.py` form error handler (lines 529, 584)
- **Notification delete**: missing `await` on `db.delete()` in `notifications.py`
- **Query params crash**: uncaught `int()` on invalid pagination params (`?page=abc`) in companies, projects, ar-content list pages
- **Yandex Disk `DiskPathFormatError`**: `_ensure_directory` now skips `app:` as directory
- **Video proxy streaming**: rewrote YD proxy to support HTTP Range requests (partial content 206)

### Security
- Removed debug endpoint `/debug/storage-test` (leaked filesystem paths in production)
- Added `get_current_active_user` auth dependency on all backup API endpoints
- Input validation: clamped `backup_retention_days` and `backup_max_copies` to positive values
- `pg_dump` timeout (10 min) to prevent hanging on unresponsive database

### Removed
- `temp_page.html` — temporary file
- `requirements_minimal.txt` — outdated subset
- `WORK_DESCRIPTION.md` — one-time work report
- `scripts/backup/cron-backups.example` — replaced by APScheduler
- `scripts/backup/continuous-backup.sh` — replaced by APScheduler
- `scripts/backup/backup-test.sh` — replaced by APScheduler
- `docs/VIDEO_ROTATION_ANALYSIS.md` — one-time analysis
- `docs/COMPETITOR_ANALYSIS_OJV_WEBAR.md` — one-time analysis
- `docs/FIX_PREVIEW_LINKS_QR.md` — resolved fix report

## [2.0.1] - 2026-02-14

### Added
- **Video Playback Modes**: manual, sequential, cyclic rotation
- **Automatic Video Rotation**: videos switch after playback ends in AR viewer
- Playback mode API endpoint

### Fixed
- Rotation state not updating in viewer
- Sequential mode returning wrong video
- Video rotation type values corrected

## [2.0.0] - Initial Release

### Features
- User management and JWT authentication
- Company and project management
- AR content creation and management
- Media file storage and management
- AR marker generation
- Preview and thumbnail generation
- OAuth integrations (Yandex)
- API documentation (Swagger/OpenAPI)
- Docker containerization
- Automatic database migrations (Alembic)
- Notification system
- Analytics and statistics dashboard
