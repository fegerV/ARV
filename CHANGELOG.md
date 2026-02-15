# Changelog

All notable changes to this project will be documented in this file.

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
