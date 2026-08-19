# Security Audit Report — V-Portal (E:\Project\ARV)

**Date:** 2026-08-19  
**Scope:** SSRF, XSS, File Upload Security, Business Logic Security  
**Overall Risk:** CRITICAL — Multiple unauthenticated endpoints and input-validation bypasses found.

---

## 1. SSRF (Server-Side Request Forgery) & Open Redirect

### 1.1 Open Redirect via Referer header — **HIGH**

| File | Line |
|------|------|
| `app/html/routes/auth.py` | 94–95 |

```python
94:    redirect_to = request.headers.get("referer") or "/admin"
95:    return RedirectResponse(url=redirect_to, status_code=303)
```

The `admin_set_language` endpoint (POST `/admin/language`) takes the `Referer` header — fully client controlled — and uses it as the redirect target. An attacker can host a page that auto-submits the language form with a crafted `Referer: https://evil.com`, causing any authenticated admin who visits the page to be redirected to an attacker-controlled site. No whitelist or same-origin check is applied.

### 1.2 Unvalidated redirect to DB-stored URLs — **HIGH**

| File | Lines |
|------|-------|
| `app/api/routes/ar_content.py` | 1298–1321 |
| `app/api/routes/ar_content.py` | 1325–1348 |

```python
1317:    from fastapi.responses import RedirectResponse
1318:        return RedirectResponse(url=ar_content.marker_url)
...
1344:    from fastapi.responses import RedirectResponse
1345:        return RedirectResponse(url=ar_content.photo_url)
```

Both `/ar-content/marker/{unique_id}` and `/ar-content/image/{unique_id}` issue a `302` redirect to a URL read directly from the database (`marker_url`, `photo_url`). While the primary creation path builds these via `build_public_url()` (safe), the **legacy mass-assignment endpoint** (`update_video`, see §4.2) and the **unauthenticated update endpoints** can populate `video_url` / `marker_url` with arbitrary attacker-supplied URLs. The ARCore mobile client follows these redirects, enabling a blind-redirect SSRF chain and potential exfiltration of the Yandex Disk OAuth bearer token from the `Authorization` header (see §1.3).

### 1.3 External HTTP requests with Yandex OAuth token — **MEDIUM**

| File | Lines |
|------|-------|
| `app/core/yandex_disk_provider.py` | 108–127 |
| `app/core/yandex_disk_provider.py` | 172–173 |

```python
163:    async with httpx.AsyncClient(timeout=_UPLOAD_TIMEOUT) as client:
164:        resp = await client.get(f"{_DISK_API}/resources/download", ...)
165:        # ...resp.raise_for_status()
170:        download_url = resp.json()["href"]
172:        dl_resp = await client.get(download_url, follow_redirects=True)
```

The download URL (`download_url`) is obtained from the Yandex Disk API and then fetched with `follow_redirects=True`. While the base API endpoint is hardcoded to `https://cloud-api.yandex.net/v1/disk`, the **Yandex-provided `href`** (a temporary download link) is fetched without verifying that its redirect chain stays within Yandex-controlled infrastructure. If Yandex's redirect were ever abused or a token were compromised, this could be chained for internal network access.

### 1.4 Unauthenticated `/api/storage/connections/{id}/stats` path traversal — **HIGH**

| File | Lines |
|------|-------|
| `app/api/routes/storage.py` | 106–117 |
| `app/core/storage_providers.py` | 125–129 |

```python
# storage.py:107
async def get_storage_stats(connection_id: int, path: str = "", ...):
    storage_provider = get_storage_provider_instance()
    stats = await storage_provider.get_usage_stats(path)

# storage_providers.py:125-129
def _get_full_path(self, storage_path: str) -> Path:
    storage_path = storage_path.lstrip('/')
    return self.base_path / storage_path
```

The `path` query parameter is passed directly to `_get_full_path` with **no `..` sanitization**. A request to:

```
GET /api/storage/connections/1/stats?path=../../etc
```

resolves to `base_path/../../etc` and performs a recursive `rglob("*")` over arbitrary directories on the server (directory listing / file count / total size), leaking filesystem structure. The endpoint also has **no authentication** (no `Depends(get_current_active_user)`).

### 1.5 No network egress filtering on Yandex Disk API calls — **MEDIUM**

The `YandexDiskStorageProvider` and all OAuth/httpx calls (in `oauth.py`, `companies.py`, `notifications.py`, `alert_service.py`) follow redirects without restricting the destination. `client.put(upload_url, ...)` (yandex_disk_provider.py:121) follows a Yandex-provided upload URL with `Content-Type: application/octet-stream` and writes attacker-controlled file content — if the `upload_url` were a data-exfiltration endpoint, content uploaded by a victim could be leaked.

---

## 2. XSS (Cross-Site Scripting)

### 2.1 Reflected XSS via `innerHTML` in `showToast()` — **CRITICAL**

| File | Lines |
|------|-------|
| `templates/base.html` | 101–129 |
| `templates/base_auth.html` | 82–106 |

```javascript
110:    toast.innerHTML = `
111:        <div class="flex items-center justify-between">
112:            <span>${message}</span>
113:            <button onclick="removeToast('${toastId}')" ...>×</button>
114:        </div>
115:    `;
```

The `showToast(message, type)` function injects `message` directly into `innerHTML` via template literal with **zero sanitization**. The `message` parameter is supplied from multiple call sites with **API response data**:

| Template | Line | Vulnerable call |
|----------|------|-----------------|
| `templates/settings.html` | 133 | `window.showToast(data.detail \|\| '...', 'error')` |
| `templates/settings.html` | 152 | `window.showToast(data.detail \|\| '...', 'error')` |
| `templates/settings.html` | 171 | `window.showToast(data.detail \|\| '...', 'error')` |
| `templates/companies/list.html` | 138 | `this.showToast(errorMessage, 'error')` |
| `templates/ar-content/list.html` | 86 | `this.showToast(error.message \|\| '...', 'error')` |

API error `detail` fields routinely contain user-controlled or externally-reflected content, e.g.:

| File | Line | Content reflected |
|------|------|-------------------|
| `app/api/routes/ar_content.py` | 808 | `detail=f"Не удалось создать AR контент: {str(e)}"` |
| `app/api/routes/companies.py` | 417 | `detail=f"Yandex OAuth error: {detail}"` where `detail = resp.json().get("error_description", resp.text)` |
| `app/api/routes/oauth.py` | 118 | `"response_text": response.text[:200]` (logged, but similar pattern) |

**Exploit chain:** An attacker submits a value that triggers an API error containing an HTML payload (e.g., via the legacy video update endpoint's mass assignment reflecting a crafted `error_description` from Yandex), the error `detail` flows into `data.detail`, and `showToast` renders it as live HTML — executing `alert(document.cookie)` or session-stealing scripts in the admin's browser.

### 2.2 Stored XSS via `innerHTML` in `showModal()` — **HIGH**

| File | Line |
|------|------|
| `templates/base.html` | 181–184 |

```javascript
181:    function showModal(content) {
182:        document.getElementById('modal-body').innerHTML = content;
```

`showModal(content)` writes arbitrary HTML into `modal-body` via `innerHTML`. If `content` originates from an HTMX response or API payload containing user data, this is a stored-XSS vector.

### 2.3 Unescaped alert content in admin email — **MEDIUM**

| File | Lines |
|------|-------|
| `app/services/alert_service.py` | 120–125 |

```python
125:    {''.join([f'<div ...><h4>{a.title}</h4><p>{a.message}</p></div>' for a in alerts])}
```

`Alert.title` and `Alert.message` are inserted into the HTML email body **without escaping**. While alert data currently originates from system monitoring metrics, any future code path that interpolates user-controlled data (e.g., company name, project name into alert metrics) would create a stored-XSS-in-email vector.

### 2.4 `Markup()` in Jinja2 filters — **LOW**

| File | Lines |
|------|-------|
| `app/html/filters.py` | 10–20, 42–68 |

The `datetime_format` filter returns `Markup("—")` (safe). The `tojson_filter` returns `Markup(...)` for JSON embedded in `<script type="application/json">` blocks. This is the **correct** pattern (JSON in non-executable script blocks with `</` escaped to `<\/`). No vulnerability, but worth noting that any future move of `tojson` output into a `<script>` (executable) context would be exploitable.

### 2.5 Templates — autoescaping is enabled (SAFE)

FastAPI's `Jinja2Templates` enables autoescaping for `.html` files. No `|safe` filters were found in any template. Jinja2 `{{ }}` variables (e.g., `{{ item.customer_name }}`, `{{ ar_content.order_number }}`) are auto-escaped. The `| e` filter is additionally applied in JS `@click` contexts (e.g., `list.html:193`, `list.html:205`, `list.html:231`).

---

## 3. File Upload Security

### 3.1 No MIME-type / magic-byte validation on photo uploads — **CRITICAL**

| File | Lines |
|------|-------|
| `app/api/routes/ar_content.py` | 261–269 |
| `app/utils/ar_content.py` | 366–377 |

```python
262:    allowed_photo_extensions = ['jpeg', 'jpg', 'png']
263:    allowed_video_extensions = ['mp4', 'webm', 'mov']
265:    if not validate_file_extension(photo_file.filename, allowed_photo_extensions):
266:        raise HTTPException(status_code=422, detail="Photo must be JPEG or PNG")
```

**Only the file extension is checked** — `Path(filename).suffix.lower()`. The MIME type and magic bytes (file signature) are **never verified**. An attacker can upload a `.jpg` file that is actually:
- A polyglot (valid JPEG + embedded executable/script)
- A file with a renamed extension containing malicious content

The `EnhancedValidationService` (which checks magic bytes via `python-magic` at `enhanced_validation_service.py:259`) exists but is **never called** in the upload path — it is only used by the `/api/v2/media/validation/validate` endpoint, which itself has no auth (see §4.1).

### 3.2 No photo file size limit enforced — **HIGH**

| File | Line |
|------|------|
| `app/core/config.py` | 103 |
| `app/api/routes/ar_content.py` | 125–133 |

`MAX_FILE_SIZE_PHOTO` (10 MB) is defined in config but is **never referenced or checked** in the upload path. The `validate_file_size()` function (ar_content.py:131) is defined but **never called**. Only video uploads enforce a size limit (500 MB via `save_uploaded_video` at `video_utils.py:230`).

### 3.3 `eval()` on ffprobe output — **HIGH** (code injection)

| File | Line |
|------|-------|
| `app/services/enhanced_validation_service.py` | 382 |

```python
382:    'fps': eval(video_stream.get('r_frame_rate', '0/1')),
```

`eval()` is called on the `r_frame_rate` field from ffprobe JSON output. ffprobe parses the **video file's own metadata**, which is fully attacker-controlled. A crafted video file can embed an arbitrary `r_frame_rate` value such as `__import__('os').system('id')`, achieving **remote code execution** on the server. While this code path is in the enhanced validation service (not the main upload handler), it is reachable via the unauthenticated `/api/v2/media/validation/validate` endpoint.

### 3.4 No filename sanitization on stored video filename — **MEDIUM**

| File | Line |
|------|-------|
| `app/api/routes/videos.py` | 309 |

```python
309:    filename=upload_file.filename,
```

The raw uploaded filename is stored directly in the `Video.filename` column. While `generate_video_filename()` (line 320) sanitizes the on-disk filename, the original `upload_file.filename` is persisted to the DB and returned in API responses. A filename like `evil'.png"><script>alert(1)</script>` would be stored and later rendered in templates (though auto-escaping mitigates direct XSS, it remains a data-integrity and injection concern).

### 3.5 `LocalStorageProvider._get_full_path` — no path-traversal guard — **HIGH**

| File | Lines |
|------|-------|
| `app/core/storage_providers.py` | 125–129 |

```python
125:    def _get_full_path(self, storage_path: str) -> Path:
126:        storage_path = storage_path.lstrip('/')
127:        return self.base_path / storage_path
```

Only `lstrip('/')` is applied — `../../` sequences pass through. This is exploitable via the unauthenticated `/api/storage/connections/{id}/stats` endpoint (§1.4) for directory listing, and could be leveraged for `get_file` / `delete_file` if any route calls those methods with user input.

### 3.6 StaticFiles mount serves from `STORAGE_BASE_PATH` without per-file access control — **LOW**

| File | Lines |
|------|-------|
| `app/main.py` | 453 |

```python
453:    app.mount("/storage", StaticFiles(directory=storage_dir), name="storage")
```

All storage files (including AR content photos, videos, QR codes) are **world-readable** via `/storage/...` with no authentication or access control. File paths are predictable (`VertexAR/{project_slug}/{order_number}/photo.jpg`). Anyone who can guess or enumerate `order_number` and project slugs (which are derived from company/project names) can access media directly.

---

## 4. Business Logic Security

### 4.1 Complete absence of authentication on video, AR-content, analytics, and enhanced-media endpoints — **CRITICAL**

The following API route modules have **ZERO** `Depends(get_current_active_user)` imports or dependencies on ANY endpoint:

| File | Routes without auth | Impact |
|------|---------------------|--------|
| `app/api/routes/videos.py` | `upload_videos`, `list_videos`, `set_video_active`, `update_video_subscription`, `update_video_rotation`, `update_video_active_flag`, `update_playback_mode`, `list/create/update/delete` schedule CRUD, `update_video` (legacy), `delete_video` | Unauthenticated video upload, deletion, subscription manipulation |
| `app/api/routes/ar_content.py` | `list_all_ar_content`, `create_ar_content`, `create_ar_content_hierarchical`, `create_ar_content_legacy`, `regenerate_media`, `get_ar_content`, `get_ar_content_by_id`, `delete_ar_content`, `delete_ar_content_by_id`, `update_ar_content`, `validate_marker`, `get_ar_marker`, `get_ar_image`, `analyze_photo_quality` | Unauthenticated AR content creation/deletion, file uploads |
| `app/api/routes/analytics.py` | `analytics_overview`, `analytics_summary`, `analytics_company`, `analytics_project`, `analytics_content`, `track_ar_session`, `mobile_session_start`, `ar_diagnostic_event`, `mobile_analytics_update` | Unauthenticated analytics access and data injection |
| `app/api/routes/enhanced_media.py` | All 9 endpoints (`generate_thumbnail`, `validate_file`, `validate_batch_files`, `get_media_info`, `get_system_health`, etc.) | Unauthenticated file validation, thumbnail generation, system health disclosure, cache manipulation |
| `app/api/routes/storage.py` | `create_connection`, `test_connection`, `get_storage_stats`, `set_company_storage`, `list_storage_connections`, `proxy_yandex_disk_file` | Unauthenticated storage management |
| `app/api/routes/notifications.py` | `test_notification` (line 241) | Unauthenticated email/Telegram spam (see §4.5) |
| `app/api/routes/public.py` | All (intentionally public) | OK for viewer-facing endpoints |
| `app/api/routes/viewer.py` | All (intentionally public) | OK for AR viewer app |

Only `auth.py`, `companies.py`, `backups.py`, `projects.py`, `notifications.py` (most routes), and `rotation.py` (`get_current_user_optional`) enforce authentication. The CSRF middleware (`csrf.py:70`) skips validation when no `access_token` cookie is present, so unauthenticated API requests bypass CSRF entirely.

### 4.2 Mass assignment via legacy video update endpoint — **CRITICAL**

| File | Lines |
|------|-------|
| `app/api/routes/videos.py` | 991–1006 |

```python
991:    async def update_video(video_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
992:        """Legacy endpoint - use specific PATCH endpoints instead."""
...
1002:    for k, val in payload.items():
1003:        if hasattr(v, k):
1004:            setattr(v, k, val)
```

The legacy `PUT /api/videos/{video_id}` accepts a **raw `dict` payload** and calls `setattr(v, k, val)` for **every attribute** that exists on the `Video` model. There is **no allow-listing**. An attacker can set:
- `subscription_end` to any future date → **subscription bypass** (extend video subscription indefinitely)
- `is_active` → True → force a video to be active
- `video_url` to an arbitrary external URL → SSRF payload for the mobile AR client
- `rotation_type`, `rotation_weight`, `rotation_order` → manipulate playback order

No authentication, no CSRF, no field allow-list, no validation.

### 4.3 Race condition on first-video selection — **MEDIUM**

| File | Lines |
|------|-------|
| `app/api/routes/videos.py` | 279–282, 361–363 |

```python
279:    existing_videos_count = await db.scalar(
280:        select(func.count(Video.id)).where(Video.ar_content_id == content_uuid)
281:    )
282:    is_first_video = existing_videos_count == 0
...
361:    if is_first_video and len(created_videos) == 0:
362:        video.is_active = True
363:        ar_content.active_video_id = video.id
```

Between the count check (line 279) and the commit (line 365), a concurrent upload can pass the same `is_first_video == True` check. Both uploads set `video.is_active = True` and `ar_content.active_video_id = video.id` — the last commit wins, resulting in **inconsistent state** (multiple videos marked active, or the wrong video set as active). No transaction isolation or locking is used.

### 4.4 Unrestricted `duration_years` / subscription bypass — **HIGH**

| File | Lines |
|------|-------|
| `app/api/routes/ar_content.py` | 252–253, 652 |

```python
252:    if duration_years < 1:
253:        raise HTTPException(status_code=400, detail="duration_years must be >= 1")
...
652:    duration_years: int = Form(30),
```

`duration_years` is accepted from user form input with **no upper bound** and **no server-side subscription-plan check**. A user can set `duration_years=99999`, making the AR content valid for ~273,000 years. Combined with the missing authentication on `create_ar_content` (§4.1), anyone can create indefinitely-valid AR content.

### 4.5 Unauthenticated email/Telegram spam via test notification endpoint — **HIGH**

| File | Lines |
|------|-------|
| `app/api/routes/notifications.py` | 241–255 |

```python
241:    async def test_notification(email: str, chat_id: str, background_tasks: BackgroundTasks):
242:        background_tasks.add_task(_send_email_notification_sync, email, "Test Email", "<p>V-Portal test email</p>")
249:        background_tasks.add_task(_send_telegram_notification_async, chat_id, "V-Portal test message")
```

The `/api/notifications/test` endpoint has **no authentication** (no `Depends(get_current_active_user)`). It accepts arbitrary `email` and `chat_id` parameters and:
1. Sends an email via the configured SMTP server to **any email address** (spam/phishing relay)
2. Sends a Telegram message via the configured bot token to **any chat ID** (XSS-in-Telegram via `parse_mode: "HTML"` if message content is ever made user-controlled)

### 4.6 `views_count` increment race condition — **LOW**

| File | Lines |
|------|-------|
| `app/api/routes/viewer.py` | 750 |

```python
750:        ar_content.views_count = (ar_content.views_count or 0) + 1
```

A classic read-modify-write without a transaction lock or atomic DB increment. Under concurrent viewer requests, view counts can be **lost** (undercounted). While not directly a security exploit, it undermines the integrity of analytics revenue attribution.

### 4.7 Unauthenticated AR content creation — **CRITICAL**

| File | Lines |
|------|-------|
| `app/api/routes/ar_content.py` | 645–672, 761–810, 813–873 |

`POST /api/ar-content`, `POST /api/companies/{id}/projects/{id}/ar-content`, and the legacy `ar-content-legacy` endpoint all lack authentication. Any anonymous user can:
1. Upload arbitrary photo + video files (subject to only extension checks)
2. Create AR content under **any** company/project ID by simply supplying `company_id` and `project_id` form values — there is no verification that the requester belongs to or owns those entities
3. `validate_company_project` (line 75) only checks that the company and project exist and that the project belongs to the company — it does NOT check user authorization

This is a direct **broken access control / IDOR** vulnerability. The `_create_ar_content` function does not accept or verify a `current_user` parameter.

### 4.8 Token-encryption fallback to base64 — **MEDIUM**

| File | Line |
|------|-------|
| `app/utils/token_encryption.py` | 36–51, 55–61, 68–74 |

When Fernet cipher initialization fails (e.g., `SECRET_KEY` is empty or too short), credentials silently fall back to **`base64` encoding** (not encryption). `decrypt_credentials` then attempts Fernet first, falls back to base64. A misconfigured or default `SECRET_KEY` would cause OAuth tokens to be stored in **easily reversible base64**, leaking Yandex Disk bearer tokens. The fixed salt (`b'vertex_ar_oauth_salt'`, line 30) also reduces the effectiveness of PBKDF2 against rainbow tables.

---

## Summary Table

| # | Category | Severity | File:Line | Description |
|---|----------|----------|-----------|-------------|
| 1.1 | SSRF/Open Redirect | HIGH | `app/html/routes/auth.py:94-95` | Open redirect via `Referer` header |
| 1.2 | SSRF/Open Redirect | HIGH | `app/api/routes/ar_content.py:1318,1345` | Unvalidated redirect to DB-stored URLs |
| 1.4 | SSRF/Path Traversal | HIGH | `app/api/routes/storage.py:107` + `storage_providers.py:125-129` | Path traversal via `path` param on unauthenticated endpoint |
| 4.1 | Broken Access Control | CRITICAL | `videos.py`, `ar_content.py`, `analytics.py`, `enhanced_media.py`, `storage.py` | No authentication on 30+ endpoints |
| 4.2 | Mass Assignment | CRITICAL | `videos.py:1002-1004` | Raw `setattr` on all model fields via legacy endpoint |
| 4.3 | Race Condition | MEDIUM | `videos.py:279-282,361-363` | First-video selection race |
| 4.4 | Business Logic | HIGH | `ar_content.py:252-253,652` | Unbounded `duration_years` — subscription bypass |
| 4.5 | Abuse | HIGH | `notifications.py:241-255` | Unauthenticated email/Telegram spam |
| 4.7 | Broken Access Control | CRITICAL | `ar_content.py:645-672` | Unauthenticated AR content creation with IDOR |
| 3.1 | File Upload | CRITICAL | `ar_content.py:262-269`, `ar_content.py:366-377` | Extension-only validation, no magic bytes |
| 3.2 | File Upload | HIGH | `ar_content.py:125-133` | `MAX_FILE_SIZE_PHOTO` defined but never enforced |
| 3.3 | Code Injection | HIGH | `enhanced_validation_service.py:382` | `eval()` on ffprobe metadata |
| 3.4 | File Upload | MEDIUM | `videos.py:309` | Raw filename stored in DB |
| 3.5 | Path Traversal | HIGH | `storage_providers.py:125-129` | No `..` sanitization in `_get_full_path` |
| 2.1 | XSS | CRITICAL | `base.html:110-115`, `base_auth.html:90-95` | `innerHTML` with unsanitized `message` from API errors |
| 2.2 | XSS | HIGH | `base.html:182` | `showModal` innerHTML injection |
| 2.3 | XSS (email) | MEDIUM | `alert_service.py:120-125` | Unescaped alert title/message in HTML email |
