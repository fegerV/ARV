# AR Content API Documentation

## Endpoints

### Get AR Content Detail
```
GET /api/ar-content/{id}
```

Retrieves detailed information about a specific AR content item.

**Rate Limit**: 30 requests per minute

**Response**:
```json
{
  "id": 1,
  "unique_id": "uuid-string",
  "title": "AR Content Title",
  "description": "Description of the content",
  "company_id": 1,
  "company_name": "Company Name",
  "project_id": 1,
  "project_name": "Project Name",
  "image_url": "http://example.com/image.jpg",
  "thumbnail_url": "http://example.com/thumbnail.jpg",
  "image_width": 1920,
  "image_height": 1080,
  "image_size_readable": "2.4 MB",
  "image_path": "/path/to/image.jpg",
  "marker_status": "ready",
  "marker_url": "http://example.com/marker.mind",
  "marker_path": "/path/to/marker.mind",
  "marker_feature_points": 120,
  "videos": [
    {
      "id": 1,
      "title": "Video Title",
      "video_url": "http://example.com/video.mp4",
      "thumbnail_url": "http://example.com/video_thumb.jpg",
      "duration": 30.5
    }
  ],
  "rotation_rule": {
    "type": "daily_cycle",
    "type_human": "Ежедневная ротация",
    "default_video_title": "Default Video",
    "next_change_at": "2023-12-01T00:00:00Z",
    "next_change_at_readable": "01.12.2023 00:00"
  },
  "stats": {
    "views": 100,
    "unique_sessions": 80,
    "avg_duration": 25.5,
    "avg_fps": 29.7
  },
  "created_at": "2023-11-01T10:30:00Z",
  "expires_at": "2024-11-01T10:30:00Z"
}
```

### List AR Content
```
GET /api/ar-content
```

Lists AR content items with filtering and pagination support.

**Rate Limit**: 60 requests per minute

**Query Parameters**:
- `page` (int, default: 1) - Page number
- `per_page` (int, default: 25, max: 100) - Items per page
- `search` (string) - Search in title and description
- `company_id` (int) - Filter by company
- `project_id` (int) - Filter by project
- `marker_status` (string) - Filter by marker status
- `is_active` (boolean) - Filter by active status
- `date_from` (datetime) - Filter by creation date (from)
- `date_to` (datetime) - Filter by creation date (to)

**Response**:
```json
{
  "items": [
    {
      "id": 1,
      "unique_id": "uuid-string",
      "title": "AR Content Title",
      "description": "Description of the content",
      "company_id": 1,
      "company_name": "Company Name",
      "project_id": 1,
      "project_name": "Project Name",
      "image_url": "http://example.com/image.jpg",
      "thumbnail_url": "http://example.com/thumbnail.jpg",
      "videos_count": 5,
      "marker_status": "ready",
      "views_count": 100,
      "created_at": "2023-11-01T10:30:00Z",
      "expires_at": "2024-11-01T10:30:00Z"
    }
  ],
  "meta": {
    "page": 1,
    "per_page": 25,
    "total": 100,
    "total_pages": 4
  }
}
```

### Create AR Content
```
POST /api/ar-content
```

Creates a new AR content item.

**Rate Limit**: 10 requests per minute

**Form Data**:
- `company_id` (int, required)
- `project_id` (int, required)
- `title` (string, required)
- `description` (string, optional)
- `image` (file, required)

**Response**:
```json
{
  "id": 1,
  "unique_id": "uuid-string",
  "image_url": "http://example.com/image.jpg",
  "marker_status": "pending",
  "marker_task_id": "task-id",
  "thumbnail_task_id": "task-id"
}
```

### Upload Video
```
POST /api/ar-content/{content_id}/videos
```

Uploads a video to an AR content item.

**Rate Limit**: 10 requests per minute

**Form Data**:
- `file` (file, required) - Video file
- `title` (string, optional) - Video title
- `is_active` (boolean, default: false) - Set as active video

**Response**:
```json
{
  "id": 1,
  "video_url": "http://example.com/video.mp4",
  "is_active": false,
  "thumbnail_task_id": "task-id"
}
```

### Generate Marker
```
POST /api/ar-content/{content_id}/generate-marker
```

Triggers marker generation for an AR content item.

**Rate Limit**: 5 requests per minute

**Response**:
```json
{
  "task_id": "task-id",
  "status": "processing_started"
}
```

### Get Active Video (Public)
```
GET /api/ar/{unique_id}/active-video
```

Gets the active video for a public AR viewer.

**Rate Limit**: 100 requests per minute

**Response**:
```json
{
  "video_url": "http://example.com/video.mp4"
}
```

### Get AR Content (Public)
```
GET /api/ar/{unique_id}
```

Gets basic information for a public AR viewer.

**Rate Limit**: 100 requests per minute

**Response**:
```json
{
  "id": 1,
  "unique_id": "uuid-string",
  "marker_status": "ready",
  "marker_url": "http://example.com/marker.mind",
  "image_url": "http://example.com/image.jpg"
}
```

## Error Handling

All endpoints return a consistent error format:

```json
{
  "detail": "Error message",
  "code": "ERROR_CODE",
  "meta": {
    "additional": "information"
  }
}
```

Common error codes:
- `AR_CONTENT_NOT_FOUND` - AR content not found (404)
- `VALIDATION_ERROR` - Request validation failed (422)
- `INTERNAL_ERROR` - Internal server error (500)
- `RATE_LIMIT_EXCEEDED` - Rate limit exceeded (429)

## Rate Limiting

Rate limits are implemented at both the application and Nginx levels:
- Application-level using slowapi
- Nginx-level for additional protection

When a rate limit is exceeded, a 429 status code is returned with the message "Rate limit exceeded".