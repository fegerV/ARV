# Deep Authentication Audit Report

## 1. Authentication Flow

### Register (`POST /api/auth/register` — `auth.py:364`)
- **Admin-gated**: Only authenticated admin users can register new users (`get_current_active_user` dependency enforced).
- **Password policy**: Only `min_length=8` from Pydantic schema. No complexity requirements, no max length.
- **Role assignment**: `role` is a free-form string from request body. Any admin can self-escalate or create new admins. No RBAC enforcement on role values.
- **No email verification**: User is created with `is_active=True` immediately. No verification token, no email confirmation.

### Login (`POST /api/auth/login` — `auth.py:338`, `POST /admin/login-form` — `auth.py:445`)
- **Rate limiting (API)**: 10 requests/minute via `@limiter.limit("10/minute")` decorator. Applied correctly.
- **Rate limiting (HTML login page GET)**: `limiter.limit("5/minute")` is **called** on `auth.py:347` but the returned decorator is **not applied** — the rate limit is NOT enforced on the HTML login page render.
- **Rate limiting (HTML login POST)**: No `@limiter.limit` decorator on `admin_login_form`. Only account-level lockout (5 failed attempts → 15-min lockout via `locked_until` field).
- **Password verification**: `verify_password()` at `auth.py:94` supports both `pbkdf2_sha256` (passlib default) and legacy `SHA-256` (pre-2025 users). Password rehash occurs on login if `needs_password_rehash()` returns True.
- **MFA**: Telegram 6-digit OTP enforced only on HTML admin login (`/admin/login-2fa`). **NOT available on API login** (`/api/auth/login`). No TOTP, no hardware key, no backup codes.

### Access Token (`auth.py:383`)
- **Algorithm**: HS256 (symmetric). Config at `config.py:JWT_ALGORITHM = "HS256"`.
- **Payload**: `{"sub": user.email, "user_id": user.id, "exp": datetime}`. No `role` or `permissions` claim in the JWT itself.
- **TokenData schema**: Has `role` field but it is **never written to or read from the token**. Role is always looked up from DB on each request by email.
- **Expiration**: Configurable via `session_timeout` DB setting. Default 1440 minutes (24 hours).
- **`OAuth2PasswordBearer`**: Defined at `auth.py:30` as `OAuth2PasswordBearer(tokenUrl="login")` but **never imported or used anywhere**. Token extraction is done manually via `_extract_request_token()` at `auth.py:78`.

### Refresh Tokens (`auth.py:65`)
- **NOT IMPLEMENTED**. The `get_current_user` function (which decodes tokens) contains a comment: `# Note: Currently no refresh token mechanism`. No refresh endpoint, no refresh token storage, no `refresh` claim in JWT.
- Tokens are stateless JWTs — the only way to "refresh" is to re-authenticate.

### Logout (`POST /api/auth/logout` — `auth.py:255`, `POST /admin/logout` — `auth.py:309`)
- **Cookie clearing only**: Clears `access_token` and `csrf_token` cookies. On HTML: also clears `language` and pops session state.
- **No server-side revocation**: JWT remains cryptographically valid until expiry. Logout does not invalidate the token.
- **No token blacklist**: There is no mechanism to reject a previously-logged-out token.

### Token Revocation
- **Not implemented**. No server-side session store, no blacklist/allowlist, no `jti` (JWT ID) claim, no introspection endpoint.

### MFA (Multi-Factor Authentication) (`auth.py:169`)
- **Telegram-based OTP**: 6-digit code delivered via Telegram bot to the user's registered `telegram_id`. Stored in Redis with key `2fa:pending:{pending_token}` and TTL of 300 seconds.
- **Availability**: HTML login only. API login (`/api/auth/login`) does **not** support MFA — any API-authenticated session is single-factor only.
- **No TOTP**: No `otpauth://` URI support, no authenticator app integration.
- **No hardware keys**: No WebAuthn/FIDO2 support.

## 2. Token Extraction & Verification (`auth.py:65`)

- **Sources**: Token checked in order: explicit `token` parameter → `Authorization: Bearer` header → `access_token` cookie.
- **Decoding**: `decode_token()` at `auth.py:55` uses `jwt.decode()` with the same secret key and algorithm. Validates `exp` (expiry) and raises `HTTPException(401)` on `JWTError` or token expiry.
- **User lookup**: Email from `sub` claim is used to query the DB for the user record. If user doesn't exist, 401 is returned.
- **Active check**: `get_current_active_user` additionally checks `user.is_active` and raises 400 if inactive.

## 3. CSRF Protection

- **Middleware**: `CSRFMiddleware` applied application-wide.
- **Protected**: All state-changing requests (POST, PUT, DELETE, PATCH).
- **Exempt paths**: Login (`/api/auth/login`, `/admin/login-form`) and static files (`/static/`, `/openapi.json`, `/docs`, `/favicon.ico`).
- **Token source**: `X-CSRF-Token` header, validated against the `csrf_token` cookie.
- **Vulnerability**: The HTML login form path `/admin/login` (GET) is exempt from CSRF (correct — no session yet), but `/admin/login-2fa` is also in the exempt list. This means an attacker could potentially perform login CSRF during the 2FA step, though the pending-token mechanism provides some mitigation.

## 4. Auth Bypass Issues

### CRITICAL: No Auth on AR Content API Endpoints (`ar_content.py`)

None of the following endpoints have any auth dependency — they accept `company_id` and `project_id` directly from the request:

| Endpoint | Method | Path | Impact |
|---|---|---|---|
| `create_ar_content` | POST | `/api/ar-content` | Anyone can create AR content, upload files, assign to any company/project |
| `_create_ar_content` | (internal) | — | Internal function called by the above, also has no user context |
| `list_ar_content` | GET | `/api/companies/{cid}/projects/{pid}/ar-content` | Anyone can list all AR content for any company |
| `get_ar_content_by_id` | GET | `/api/ar-content/{content_id}` | Anyone can read any AR content by ID (IDOR) |
| `get_ar_content_by_unique_id` | GET | `/api/ar-content/by-unique/{unique_id}` | Public by unique link — may be intentional, but no rate limiting |
| `update_ar_content` | PUT | `/api/ar-content/{content_id}` | Anyone can modify any AR content |
| `delete_ar_content` | DELETE | `/api/ar-content/{content_id}` | Anyone can delete any AR content |
| `regenerate_ar_media` | POST | `/api/ar-content/{content_id}/regenerate-media` | Anyone can trigger media regeneration (expensive operation) |
| `validate_marker` | POST | `/api/ar-content/{content_id}/validate-marker` | Anyone can validate markers |

### CRITICAL: No Auth on Video API Endpoints (`videos.py`)

| Endpoint | Method | Path | Impact |
|---|---|---|---|
| `upload_video_to_project` | POST | `/api/videos/upload` | Anyone can upload videos to any project |
| `regenerate_video_thumbnail` | POST | `/api/videos/{video_id}/regenerate-thumbnail` | Anyone can trigger thumbnail regeneration |
| `modify_video` | PUT | `/api/videos/{video_id}` | Anyone can modify video metadata |
| `delete_video` | DELETE | `/api/videos/{video_id}` | Anyone can delete videos |
| `get_project_videos` | GET | `/api/companies/{cid}/projects/{pid}/videos` | Anyone can list videos for any project |
| `schedule_video` | POST | `/api/videos/schedule` | Anyone can schedule videos |
| `get_video_schedule` | GET | `/api/videos/schedule/{schedule_id}` | Anyone can read schedule data |
| `get_project_schedules` | GET | `/api/videos/schedules/{cid}/{pid}` | Anyone can list schedules |
| `update_schedule` | PUT | `/api/videos/schedule/{schedule_id}` | Anyone can modify schedules |
| `delete_schedule` | DELETE | `/api/videos/schedule/{schedule_id}` | Anyone can delete schedules |

### CRITICAL: No Auth on Storage API Endpoints (`storage.py`)

| Endpoint | Method | Path | Impact |
|---|---|---|---|
| `create_storage_connection` | POST | `/api/connections` | Anyone can create storage connections |
| `test_storage_connection` | POST | `/api/connections/{id}/test` | Anyone can test storage connections (credential exposure) |
| `list_storage_connections` | GET | `/api/connections` | Anyone can list all storage connections and their base paths |
| `update_company_storage` | PUT | `/api/companies/{id}/storage` | Anyone can modify company storage settings |
| `get_company_storage` | GET | `/api/companies/{id}/storage` | Anyone can read company storage configuration |
| `proxy_yandex_disk_file` | GET | `/api/yd-file` | **IDOR + data exfiltration**: Anyone can download arbitrary Yandex Disk files by providing `company_id` + `path` |

### CRITICAL: No Auth on Analytics Admin Endpoints (`analytics.py`)

| Endpoint | Method | Path | Impact |
|---|---|---|---|
| `analytics_overview` | GET | `/api/analytics/overview` | Exposes aggregate analytics data (user counts, storage usage, etc.) |
| `analytics_summary` | GET | `/api/analytics/summary` | Exposes summary statistics |
| `analytics_content` | GET | `/api/analytics/content` | Exposes AR content analytics |
| `analytics_company` | GET | `/api/analytics/company/{id}` | Exposes per-company analytics |

### CRITICAL: WebSocket `/ws/alerts` Has No Auth (`alerts_ws.py`)

Anyone can connect to the alerts WebSocket by guessing or enumerating session IDs. No token validation, no user context.

### HIGH: Debug Endpoint Leaks Sensitive Data (`debug.py:7`)

`GET /debug-auth` returns:
- Whether the user is authenticated
- User ID, email, active status
- **All cookies** (including session/CSRF tokens)
- **All HTTP headers** (including Authorization tokens if present)

This endpoint has no auth and should be removed or restricted to dev mode only.

### HIGH: Account Lockout Only on HTML Login (`auth.py:445`)

The API login endpoint (`/api/auth/login`) has **no account lockout mechanism** — only rate limiting (10/min). The HTML login form has both rate limiting (broken — see below) and account lockout (5 attempts → 15 min). An attacker can brute-force API login without triggering lockout.

### HIGH: Broken Rate Limit Decorator on HTML Login Page (`auth.py:347`)

```python
@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    limiter.limit("5/minute")  # NOT a decorator — just returns a decorator function, unused
    return _render_login(request)
```

`limiter.limit("5/minute")` **returns** a decorator function but is never applied to the function. The rate limit is **not enforced** on `GET /admin/login`.

### HIGH: No Session Management

- No server-side session tracking
- No session expiry/refresh
- No "active sessions" list for users
- No session invalidation on password change (tokens remain valid until expiry)
- No "remember this device" / trusted device tracking

### HIGH: No Password Policy Beyond Length

- Only `min_length=8` enforced
- No maximum length (theoretically allows DoS via very long passwords)
- No complexity requirements (uppercase, lowercase, digits, specials)
- No breach checking (HaveIBeenPwned or similar)

### HIGH: `get_current_user` Exports But Never Used

The function `get_current_user` (without the `_optional` suffix or `_active` suffix) at `auth.py:65` is listed in `__all__` but is **never used as a dependency** anywhere in the codebase. It decodes tokens and returns the user or None, but since no route uses it, it's dead code. The `get_current_user_from_cookie` function is also defined but unused.

### MEDIUM: `OAuth2PasswordBearer(tokenUrl="login")` Is Defined But Never Used

Defined at `auth.py:30`, but nowhere in the codebase is `OAuth2PasswordBearer` imported or used as a dependency. The `tokenUrl` value is only used for OpenAPI documentation, not for actual token flow. Token extraction is done manually.

### MEDIUM: No CSRF Token Rotation

CSRF token is set on login but **never rotated**. If a CSRF token is leaked (e.g., via the debug endpoint), it remains valid indefinitely (until cookie expiry).

### MEDIUM: HTML Login Form Has No CSRF-Protected Rate Limiting

The `admin_login_form` POST endpoint has no `@limiter.limit` decorator. The `admin_login_page` GET endpoint has a broken rate limiter (see above). Only account-level lockout provides protection on the HTML side.

### MEDIUM: `albums.py` HTML Route Uses No Auth

The HTML route for albums (if it exists) or the `albums.py` reference in `__init__.py` — need to verify. All HTML routes except `auth.py` and `debug.py` use `get_current_user_optional` + `require_active_user`. But the optional variant means unauthenticated access still renders the page (with limited data).

### LOW: Token Not Rotated on Re-login

Calling login while already authenticated issues a new token but does not invalidate the old one. Multiple valid tokens can coexist.

### LOW: No Password History

Changing a password (no change endpoint exists, but admin password reset via shell) does not check against previous passwords.

## 5. Auth-Protected Endpoints (HTML Routes)

All HTML routes in `app/html/routes/` use `get_current_user_optional` + `require_active_user`:

```python
async def require_active_user(user = Depends(get_current_user_optional)):
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
```

This pattern is used in: `dashboard.py`, `analytics.py`, `storage.py`, `settings.py`, `projects.py`, `notifications.py`, `ar_content.py`, `companies.py`, `backups.py`, `logs.py`, `help_routes.py`.

**Observation**: The HTML routes use `require_active_user` (raises 401 if no user), while the API routes (e.g., `rotation.py`) use a different `_require_auth()` helper. This inconsistency means different auth failure behaviors.

## 6. Auth-Protected Endpoints (API Routes)

### Auth Routes (`auth.py`)
- `POST /api/auth/register` — `get_current_active_user` (admin only)
- `POST /api/auth/login` — no dependency (but validates credentials)
- `POST /api/auth/logout` — no dependency (clears cookies)
- `GET /api/auth/check` — `get_current_active_user`

### Rotation (`rotation.py`)
- Uses `get_current_user_optional` + `_require_auth()` helper at line 19-23:
```python
def _require_auth(user):
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
```
- Every endpoint depends on `current_user: User = Depends(_require_auth)`.
- Uses `get_current_user_optional` instead of `get_current_active_user` — means inactive users still get through the dependency chain (they'd be returned by `get_current_user_optional` if the DB lookup succeeds), but the `is_active` check happens in `get_current_active_user` which is NOT being used here.

### Analytics (`analytics.py`)
- `analytics_overview`, `analytics_summary`, `analytics_content`, `analytics_company` — **NO auth
- Other analytics endpoints — need to verify

### Backups (`backups.py`)
- `POST /api/backups/create` — `get_current_active_user`
- `POST /api/backups/create-and-download` — `get_current_active_user`

### Companies (`companies.py`)
- `GET /api/companies/` — `get_current_active_user`
- `GET /api/companies/{id}` — no auth (returns limited public data)
- `GET /api/companies/{id}/projects` — no auth (returns public project data)
- `POST /api/companies` — `get_current_active_user`
- `PUT /api/companies/{id}` — `get_current_active_user`

### Companies HTML (`html/routes/companies.py`)
- HTML route for creating/viewing companies — `get_current_user_optional` + `require_active_user`

### Projects HTML (`html/routes/projects.py`)
- HTML route for projects — `get_current_user_optional` + `require_active_user`

### Settings (`settings.py`)
- `GET /api/settings` — no auth dependency, but `get_current_user_optional` is imported and available. Only returns public settings (app_name, version, public_url).

### Viewer (`viewer.py`)
- AR viewer page — public, no auth needed

### Public (`public.py`)
- Public API routes — intentionally public (health, version)

### OAuth (`oauth.py`)
- OAuth callback handler for Yandex Disk authentication — uses state parameter and PKCE-like pattern, but should be reviewed separately for auth scope.

## 7. Auth Dependency Hierarchy

```
get_current_user_optional (auth.py:55)
  ↓ (called by)
get_current_user (auth.py:65) — UNUSED, dead code
get_current_active_user (auth.py:120) — used by protected routes
require_active_user (html/routes/__init__.py) — used by HTML routes
_require_auth (rotation.py:19) — used by rotation routes
```

**Observation**: There are three different "require auth" patterns:
1. `get_current_active_user` — raises 401 if token invalid, raises 400 if user inactive
2. `require_active_user` — wraps `get_current_user_optional`, raises 401 if no user
3. `_require_auth` (rotation.py) — wraps `get_current_user_optional`, raises 401 if no user

These should be consolidated. Pattern #2 and #3 are functionally identical.

## 8. Summary of Authentication Gaps

| Area | Status | Severity |
|---|---|---|
| AR Content API endpoints | No auth | CRITICAL |
| Video API endpoints | No auth | CRITICAL |
| Storage API endpoints | No auth | CRITICAL |
| Analytics API endpoints | No auth | CRITICAL |
| WebSocket `/ws/alerts` | No auth | CRITICAL |
| Debug endpoint | No auth, leaks data | HIGH |
| Refresh tokens | Not implemented | HIGH |
| MFA on API | Not implemented | HIGH |
| Token revocation | Not implemented | HIGH |
| Password policy | Only min_length=8 | HIGH |
| Session management | Not implemented | HIGH |
| Account lockout on API | Not implemented | HIGH |
| Broken rate limit on HTML login | Bug | HIGH |
| CSRF token rotation | Not implemented | MEDIUM |
| JWT role claims | Not used | MEDIUM |
| Multiple auth patterns | Inconsistent | MEDIUM |
| Password history | Not implemented | LOW |
| Token rotation on re-login | Not implemented | LOW |
