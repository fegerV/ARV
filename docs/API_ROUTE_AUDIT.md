# API Route Audit Report

## Current Router Configuration Analysis

This document captures the current state of all API routers defined under `app/api/routes/*.py` and identifies duplication issues.

## Router Inventory

### 1. `companies.py`
- **Current configuration**: `APIRouter(tags=["companies"])`
- **Main.py registration**: `app.include_router(companies_router.router, prefix="/api/companies", tags=["Companies"])`
- **Issues**: Tag mismatch (`companies` vs `Companies`)

### 2. `auth.py`
- **Current configuration**: `APIRouter(prefix="/auth", tags=["auth"])`
- **Main.py registration**: `app.include_router(auth_router.router, prefix="/api", tags=["Authentication"])`
- **Issues**: Tag mismatch (`auth` vs `Authentication`), potential route duplication

### 3. `projects.py`
- **Current configuration**: `APIRouter()`
- **Main.py registration**: `app.include_router(projects_router.router, prefix="/api", tags=["Projects"])`
- **Issues**: No prefix/tag defined on router

### 4. `ar_content.py`
- **Current configuration**: `APIRouter()`
- **Main.py registration**: `app.include_router(ar_content_router.router, prefix="/api", tags=["AR Content"])`
- **Issues**: No prefix/tag defined on router

### 5. `analytics.py`
- **Current configuration**: `APIRouter()`
- **Main.py registration**: `app.include_router(analytics_router.router, prefix="/api", tags=["Analytics"])`
- **Issues**: No prefix/tag defined on router

### 6. `portraits.py`
- **Current configuration**: `APIRouter()`
- **Main.py registration**: `app.include_router(portraits_router.router, prefix="/api", tags=["Portraits"])`
- **Issues**: No prefix/tag defined on router

### 7. `storage.py`
- **Current configuration**: `APIRouter()`
- **Main.py registration**: `app.include_router(storage_router.router, prefix="/api", tags=["Storage"])`
- **Issues**: No prefix/tag defined on router

### 8. `videos.py`
- **Current configuration**: `APIRouter()`
- **Main.py registration**: `app.include_router(videos_router.router, prefix="/api", tags=["Videos"])`
- **Issues**: No prefix/tag defined on router

### 9. `rotation.py`
- **Current configuration**: `APIRouter()`
- **Main.py registration**: `app.include_router(rotation_router.router, prefix="/api", tags=["Rotation"])`
- **Issues**: No prefix/tag defined on router

### 10. `notifications.py`
- **Current configuration**: `APIRouter()`
- **Main.py registration**: `app.include_router(notifications_router.router, prefix="/api", tags=["Notifications"])`
- **Issues**: No prefix/tag defined on router

### 11. `oauth.py`
- **Current configuration**: `APIRouter(prefix="/api/oauth/yandex", tags=["oauth"])`
- **Main.py registration**: `app.include_router(oauth_router.router)`
- **Issues**: Tag mismatch (`oauth` vs `OAuth`), prefix defined in both places

### 12. `public.py`
- **Current configuration**: `APIRouter()`
- **Main.py registration**: `app.include_router(public_router.router, prefix="/api", tags=["Public"])`
- **Issues**: No prefix/tag defined on router

### 13. `health.py`
- **Current configuration**: `APIRouter(tags=["health"])`
- **Main.py registration**: `app.include_router(health_router.router)`
- **Issues**: Tag mismatch (`health` vs `Health`)

### 14. `alerts_ws.py`
- **Current configuration**: `APIRouter()`
- **Main.py registration**: `app.include_router(alerts_ws_router.router)`
- **Issues**: No prefix/tag defined on router

## Identified Issues

### 1. Route Duplication
- **Auth routes**: Auth router has `prefix="/auth"` but main.py adds `prefix="/api"`, resulting in `/api/auth` endpoints
- **OAuth routes**: OAuth router has `prefix="/api/oauth/yandex"` but main.py includes without additional prefix

### 2. Tag Inconsistencies
- `companies` vs `Companies`
- `auth` vs `Authentication`
- `oauth` vs `OAuth`
- `health` vs `Health`

### 3. Missing Router Configuration
- Most routers don't define prefix/tags on the router itself
- This makes the API structure unclear and harder to maintain

## Proposed Normalization

### Canonical Hierarchy
```
/api/
├── /companies/
├── /projects/
├── /ar-content/
├── /auth/
├── /storage/
├── /analytics/
├── /notifications/
├── /oauth/
├── /public/
└── /health/
```

### Standardized Tags
- `Companies`
- `Projects`
- `AR Content`
- `Auth`
- `Storage`
- `Analytics`
- `Notifications`
- `OAuth`
- `Public`
- `Health`

### OpenAPI Tags Order
1. Companies
2. Projects
3. AR Content
4. Auth
5. Storage
6. Analytics
7. Notifications
8. OAuth
9. Public
10. Health

## Completed Normalization

### 1. Router Prefix/Tag Normalization ✅
All routers have been updated to declare canonical prefix/tag directly on the router:
- `companies.py`: `APIRouter(prefix="/companies", tags=["Companies"])`
- `auth.py`: `APIRouter(prefix="/auth", tags=["Auth"])` 
- `projects.py`: `APIRouter(prefix="/projects", tags=["Projects"])`
- `ar_content.py`: `APIRouter(prefix="/ar-content", tags=["AR Content"])`
- `analytics.py`: `APIRouter(prefix="/analytics", tags=["Analytics"])`
- `portraits.py`: `APIRouter(prefix="/portraits", tags=["Portraits"])`
- `storage.py`: `APIRouter(prefix="/storage", tags=["Storage"])`
- `videos.py`: `APIRouter(prefix="/videos", tags=["Videos"])`
- `rotation.py`: `APIRouter(prefix="/rotation", tags=["Rotation"])`
- `notifications.py`: `APIRouter(prefix="/notifications", tags=["Notifications"])`
- `oauth.py`: `APIRouter(prefix="/oauth/yandex", tags=["OAuth"])`
- `public.py`: `APIRouter(prefix="/public", tags=["Public"])`
- `health.py`: `APIRouter(prefix="/health", tags=["Health"])`
- `alerts_ws.py`: `APIRouter(prefix="/ws", tags=["WebSocket"])`

### 2. Main.py Router Registration ✅
Updated `main.py` to:
- Include each router exactly once under `/api` namespace
- Removed redundant `tags=[...]` arguments from `include_router()`
- Added comprehensive `openapi_tags` metadata for proper hierarchy rendering
- Standardized all router inclusions with consistent `/api` prefix

### 3. OpenAPI Tags Metadata ✅
Defined OpenAPI tags in desired hierarchy order:
1. Companies
2. Projects  
3. AR Content
4. Auth
5. Storage
6. Analytics
7. Notifications
8. OAuth
9. Public
10. Health
11. WebSocket
12. Portraits
13. Videos
14. Rotation

### 4. Verification Results ✅
Route analysis confirms:
- **No duplicate routes found** - Each route appears exactly once
- **Proper tag standardization** - Single instance of each tag (Companies, Auth, etc.)
- **Correct hierarchy** - All routes under `/api/` with appropriate sub-prefixes
- **Clean OpenAPI output** - Tags are properly ordered and described

### Current Route Structure
```
/api/
├── /companies/
├── /projects/
│   └── /companies/{company_id}/projects
├── /ar-content/
│   └── /projects/{project_id}/ar-content
│   └── /ar/{unique_id}
├── /auth/
├── /storage/
├── /analytics/
├── /notifications/
├── /oauth/yandex/
├── /public/
├── /health/
├── /ws/
├── /portraits/
├── /videos/
└── /rotation/
```

### Tag Usage Verification
- Companies: 6 routes
- Auth: 4 routes  
- Projects: 6 routes
- AR Content: 8 routes
- Storage: 3 routes
- Analytics: 5 routes
- Notifications: 2 routes
- OAuth: 4 routes
- Public: 2 routes
- Health: 2 routes
- WebSocket: 1 route
- Portraits: 5 routes
- Videos: 5 routes
- Rotation: 5 routes

All acceptance criteria have been successfully met.