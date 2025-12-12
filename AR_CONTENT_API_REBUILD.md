# AR Content API Rebuild - Implementation Summary

## Overview

This implementation rebuilds the AR Content API to align with the Company → Project → AR Content hierarchy as specified in the ticket.

## Key Changes Made

### 1. Model Redesign (`app/models/ar_content.py`)

**Simplified the AR Content model to include only essential fields:**
- `company_id`, `project_id` - Foreign keys with proper indexing
- `unique_id` - UUID with unique constraint (immutable)
- `name` - Simple string field (instead of title)
- `content_metadata` - JSONB for flexible metadata
- File paths and URLs: `image_path/url`, `video_path/url`, `qr_code_path/url`, `preview_url`
- `is_active`, `created_at`, `updated_at` - Standard status and timestamps

**Removed complex legacy fields:**
- Client information fields
- Marker generation fields
- Video rotation fields
- Analytics fields
- Active video relationship

### 2. Pydantic Schemas (`app/schemas/ar_content.py`)

**Created new schema structure:**
- `ARContentBase` - Core fields only
- `ARContentCreate` - For creation with company/project validation
- `ARContentUpdate` - For mutable field updates only
- `ARContentVideoUpdate` - For video replacement workflow
- `ARContentWithLinks` - Includes helper `unique_link` field
- `ARContentCreateResponse` - Response schema with all URLs

### 3. Storage Utilities (`app/utils/ar_content.py`)

**New helper functions:**
- `build_ar_content_storage_path()` - Creates nested path: `companies/{company_id}/projects/{project_id}/ar-content/{unique_id}/`
- `build_public_url()` - Converts storage paths to `/storage/...` URLs
- `build_unique_link()` - Creates `/ar-content/{unique_id}` links
- `generate_qr_code()` - Generates QR codes with unique links
- `save_uploaded_file()` - Async file upload utility

### 4. API Routes (`app/api/routes/ar_content.py`)

**Complete rebuild with nested endpoints:**

#### New Endpoint Structure:
- `GET /companies/{company_id}/projects/{project_id}/ar-content` - List content
- `POST /companies/{company_id}/projects/{project_id}/ar-content/new` - Create content
- `GET /companies/{company_id}/projects/{project_id}/ar-content/{content_id}` - Get content
- `PUT /companies/{company_id}/projects/{project_id}/ar-content/{content_id}` - Update content
- `PATCH /companies/{company_id}/projects/{project_id}/ar-content/{content_id}/video` - Replace video
- `DELETE /companies/{company_id}/projects/{project_id}/ar-content/{content_id}` - Delete content

#### Key Features:
- **Company/Project validation** - Ensures hierarchy integrity
- **Immutable unique_id** - Never changes after creation
- **QR code generation** - Automatic QR code with unique link
- **Video replacement workflow** - Replace video without changing unique_id or QR
- **Proper error handling** - 404 for missing resources, 400 for invalid hierarchy

### 5. Public API Updates (`app/api/routes/public.py`)

**Simplified public endpoints:**
- `GET /ar/{unique_id}/content` - Stream active video and metadata
- `GET /ar-content/{unique_id}` - Alias for cleaner URLs
- Removed complex video rotation logic
- Direct video URL serving

### 6. Template Routes (`app/main.py`)

**Added new template endpoint:**
- `GET /ar-content/{unique_id}` - AR viewer template with clean URL
- Maintains backward compatibility with `/ar/{unique_id}`

### 7. Storage Provider Factory (`app/services/storage/factory.py`)

**Created missing storage abstraction:**
- `BaseStorageProvider` - Abstract interface
- `LocalStorageProvider` - Full implementation
- `MinIOStorageProvider` - Placeholder for future implementation
- `YandexDiskStorageProvider` - Placeholder for future implementation
- `get_provider()` - Factory function

### 8. Database Migration (`alembic/versions/20251220_rebuild_ar_content_api.py`)

**Database schema updates:**
- Add unique constraint on `unique_id`
- Add new columns: `video_path/url`, `qr_code_path/url`, `preview_url`
- Add performance indexes on `company_id`, `project_id`, `unique_id`
- Rename `title` to `name` if needed

## Acceptance Criteria Met

✅ **Storage Structure**: Files saved under `companies/{company_id}/projects/{project_id}/ar-content/{unique_id}/`

✅ **Immutable Links**: `unique_id` and QR codes remain unchanged after updates

✅ **Video Replacement**: `PATCH .../video` swaps video while preserving unique_id and QR

✅ **Public Viewer**: Both `/ar/{uuid}` and `/ar-content/{uuid}` template endpoints work

✅ **Nested API**: All endpoints under `/api/companies/{company_id}/projects/{project_id}/ar-content`

✅ **OpenAPI Documentation**: Routes properly tagged as "AR Content"

## Testing

- ✅ Basic API endpoint tests created
- ✅ AR viewer template endpoints work
- ✅ Application imports successfully
- ✅ No syntax errors in new code

## TODOs for Future Implementation

1. **Thumbnail Generation**: Hook up existing thumbnail tasks in creation workflow
2. **Preview Generation**: Implement preview generation for videos
3. **Storage Cleanup**: Implement recursive storage folder deletion
4. **MinIO/Yandex Implementation**: Complete storage provider implementations
5. **Comprehensive Testing**: Add integration tests with database setup
6. **Error Handling**: Add more granular error responses
7. **Validation**: Add request validation for file types, sizes, etc.

## API Usage Examples

### Create AR Content
```bash
curl -X POST "http://localhost:8000/api/companies/1/projects/1/ar-content/new" \
  -F "name=My AR Content" \
  -F "image=@image.jpg" \
  -F "video=@video.mp4"
```

### Get AR Content
```bash
curl "http://localhost:8000/api/companies/1/projects/1/ar-content/123"
```

### Replace Video
```bash
curl -X PATCH "http://localhost:8000/api/companies/1/projects/1/ar-content/123/video" \
  -F "video=@new_video.mp4"
```

### Public Access
```bash
# AR viewer template
curl "http://localhost:8000/ar-content/{unique_id}"

# Content data
curl "http://localhost:8000/api/ar/{unique_id}/content"
```