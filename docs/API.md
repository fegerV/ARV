# Vertex AR B2B Platform - API Reference

## Overview

This document provides a complete reference for the Vertex AR B2B Platform API. The API follows REST principles and uses JSON for request/response payloads. All API endpoints are secured with JWT tokens for authentication and authorization.

## API Documentation

Interactive API documentation is available through Swagger UI:
- Development: `http://localhost:8000/docs`
- Production: `https://your-domain.com/docs`

Alternative documentation is available through ReDoc:
- Development: `http://localhost:8000/redoc`
- Production: `https://your-domain.com/redoc`

OpenAPI specification is available at:
- Development: `http://localhost:8000/openapi.json`
- Production: `https://your-domain.com/openapi.json`

## Overview

This document provides a complete reference for the Vertex AR B2B Platform API. The API follows REST principles and uses JSON for request/response payloads. All API endpoints are secured with JWT tokens for authentication and authorization.

## Base URL

All endpoints are prefixed with `/api/`:
- Production: `https://your-domain.com/api/`
- Development: `http://localhost:8000/api/`

## Authentication & Authorization

The API uses JWT (JSON Web Tokens) for authentication. Most endpoints require a valid access token to be included in the Authorization header.

### Obtaining Access Token

To authenticate, send a POST request to `/api/auth/login` with your credentials:

```json
{
  "email": "your-email@example.com",
  "password": "your-password"
}
```

Upon successful authentication, you'll receive a response containing the access token:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "your-email@example.com",
    "full_name": "John Doe",
    "role": "admin",
    "last_login_at": "2023-01-01T10:00:00Z"
  }
}
```

### Using the Access Token

Include the access token in the Authorization header for all authenticated requests:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Error Handling

The API returns standard HTTP status codes. Common error responses include:

| Code | Message | Description |
|------|---------|-------------|
| 400 | Bad Request | Invalid request parameters or payload |
| 401 | Unauthorized | Missing or invalid authentication token |
| 403 | Forbidden | Insufficient permissions to access resource |
| 404 | Not Found | Requested resource does not exist |
| 422 | Unprocessable Entity | Validation error for request parameters |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side error occurred |

Error response format:
```json
{
  "detail": "Error message explaining what went wrong"
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse. Default limits are:
- 100 requests per minute per IP for unauthenticated requests
- 100 requests per hour per authenticated user

Rate limit information is included in response headers:
- `X-RateLimit-Limit`: The maximum number of requests allowed
- `X-RateLimit-Remaining`: The number of requests remaining
- `X-RateLimit-Reset`: Unix timestamp when the rate limit resets

Exceeding these limits will result in a `429 Too Many Requests` response.

## Modules

The API is organized into the following modules:

1. [Authentication](#authentication)
2. [Companies](#companies)
3. [Projects](#projects)
4. [AR Content](#ar-content)
5. [Videos](#videos)
6. [Orders](#orders) *(Coming Soon)*
7. [Analytics](#analytics)
8. [Notifications](#notifications)
9. [Storage](#storage)
10. [Rotation](#rotation)
11. [OAuth](#oauth)
12. [Public](#public)
13. [Viewer](#viewer)
14. [Settings](#settings)
15. [Health](#health)
16. [WebSocket](#websocket)

---

## Authentication

### Login
- **Method**: `POST`
- **URL**: `/api/auth/login`
- **Description**: Authenticate and retrieve access token
- **Auth Required**: No

#### Parameters (Body)
```json
{
  "email": "string (required) - User's email address",
  "password": "string (required) - User's password"
}
```

#### Response (Success)
```json
{
  "access_token": "string - JWT access token",
  "token_type": "string - Token type (usually 'bearer')",
  "user": {
    "id": "int - User ID",
    "email": "string - User email",
    "full_name": "string - Full name",
    "role": "string - User role",
    "last_login_at": "datetime - Last login timestamp"
  }
}
```

#### Response (Error)
- 400: Invalid credentials or request format
- 423: Account temporarily locked due to too many failed attempts

#### Examples
```curl
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "password123"
 }'
```

### Logout
- **Method**: `POST`
- **URL**: `/api/auth/logout`
- **Description**: Log out current user
- **Auth Required**: Yes

#### Response
- 200: Successfully logged out

#### Examples
```curl
curl -X POST "http://localhost:8000/api/auth/logout" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Get Current User
- **Method**: `GET`
- **URL**: `/api/auth/me`
- **Description**: Retrieve information about the current authenticated user
- **Auth Required**: Yes

#### Response (Success)
```json
{
  "id": "int - User ID",
  "email": "string - User email",
  "full_name": "string - Full name",
  "role": "string - User role",
  "last_login_at": "datetime - Last login timestamp"
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Register User
- **Method**: `POST`
- **URL**: `/api/auth/register`
- **Description**: Register a new user account
- **Auth Required**: No

#### Parameters (Body)
```json
{
  "email": "string (required) - User's email address",
  "password": "string (required, min 8 chars) - User's password",
  "full_name": "string (required, 2-100 chars) - User's full name",
  "role": "string - User role (default: admin)"
}
```

#### Response (Success)
```json
{
  "user": {
    "id": "int - User ID",
    "email": "string - User email",
    "full_name": "string - Full name",
    "role": "string - User role",
    "last_login_at": "datetime - Last login timestamp"
  },
  "message": "string - Success message"
}
```

#### Examples
```curl
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "password123",
    "full_name": "New User",
    "role": "admin"
  }'
```

---

## Companies

### List Companies
- **Method**: `GET`
- **URL**: `/api/companies`
- **Description**: Retrieve paginated list of companies
- **Auth Required**: Yes

#### Query Parameters
```
page: int (optional, default: 1) - Page number
limit: int (optional, default: 10) - Items per page
search: string (optional) - Search term for company name or email
sort: string (optional) - Sort field (name, created_at, projects_count)
order: string (optional, default: desc) - Sort order (asc, desc)
```

#### Response (Success)
```json
{
  "items": [
    {
      "id": "string - Company ID",
      "name": "string - Company name",
      "contact_email": "string - Contact email",
      "status": "string - Company status",
      "projects_count": "int - Number of projects",
      "ar_content_count": "int - Total AR content count",
      "created_at": "datetime - Creation timestamp"
    }
  ],
  "total": "int - Total number of companies",
  "page": "int - Current page",
  "limit": "int - Items per page",
  "has_more": "bool - Whether there are more pages"
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/companies?page=1&limit=10&search=vertex" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Get Company
- **Method**: `GET`
- **URL**: `/api/companies/{company_id}`
- **Description**: Retrieve a specific company by ID
- **Auth Required**: Yes

#### Path Parameters
```
company_id: int (required) - ID of the company to retrieve
```

#### Response (Success)
```json
{
  "id": "string - Company ID",
  "name": "string - Company name",
  "contact_email": "string - Contact email",
  "status": "string - Company status",
  "projects_count": "int - Number of projects",
  "ar_content_count": "int - Total AR content count",
  "created_at": "datetime - Creation timestamp"
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/companies/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Create Company
- **Method**: `POST`
- **URL**: `/api/companies`
- **Description**: Create a new company
- **Auth Required**: Yes

#### Parameters (Body)
```json
{
  "name": "string (required, 1-255 chars) - Company name",
  "contact_email": "string (required) - Contact email address",
  "status": "string (optional) - Company status (default: ACTIVE)"
}
```

#### Response (Success)
```json
{
  "id": "string - Company ID",
  "name": "string - Company name",
  "contact_email": "string - Contact email",
  "status": "string - Company status",
  "projects_count": "int - Number of projects",
  "ar_content_count": "int - Total AR content count",
  "created_at": "datetime - Creation timestamp"
}
```

#### Examples
```curl
curl -X POST "http://localhost:8000/api/companies" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "name": "Vertex Technologies",
    "contact_email": "contact@vertex.com",
    "status": "ACTIVE"
  }'
```

### Update Company
- **Method**: `PUT`
- **URL**: `/api/companies/{company_id}`
- **Description**: Update an existing company
- **Auth Required**: Yes

#### Path Parameters
```
company_id: int (required) - ID of the company to update
```

#### Parameters (Body)
```json
{
  "name": "string (optional, 1-255 chars) - Company name",
  "contact_email": "string (optional) - Contact email address",
  "status": "string (optional) - Company status"
}
```

#### Response (Success)
```json
{
  "id": "string - Company ID",
  "name": "string - Company name",
  "contact_email": "string - Contact email",
  "status": "string - Company status",
  "projects_count": "int - Number of projects",
  "ar_content_count": "int - Total AR content count",
  "created_at": "datetime - Creation timestamp"
}
```

#### Examples
```curl
curl -X PUT "http://localhost:8000/api/companies/1" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "name": "Updated Vertex Technologies",
    "contact_email": "updated@vertex.com"
  }'
```

### Delete Company
- **Method**: `DELETE`
- **URL**: `/api/companies/{company_id}`
- **Description**: Delete a company
- **Auth Required**: Yes

#### Path Parameters
```
company_id: int (required) - ID of the company to delete
```

#### Response
- 20: Company deleted successfully

#### Examples
```curl
curl -X DELETE "http://localhost:8000/api/companies/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Projects

### List Projects for Company
- **Method**: `GET`
- **URL**: `/api/companies/{company_id}/projects`
- **Description**: Retrieve paginated list of projects for a specific company
- **Auth Required**: Yes

#### Path Parameters
```
company_id: int (required) - ID of the company
```

#### Query Parameters
```
page: int (optional, default: 1) - Page number
limit: int (optional, default: 10) - Items per page
search: string (optional) - Search term for project name
sort: string (optional) - Sort field (name, created_at, ar_content_count)
order: string (optional, default: desc) - Sort order (asc, desc)
```

#### Response (Success)
```json
{
  "items": [
    {
      "id": "string - Project ID",
      "name": "string - Project name",
      "status": "string - Project status",
      "company_id": "string - Company ID",
      "ar_content_count": "int - Number of AR content items",
      "created_at": "datetime - Creation timestamp"
    }
  ],
  "total": "int - Total number of projects",
  "page": "int - Current page",
  "limit": "int - Items per page",
  "has_more": "bool - Whether there are more pages"
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/companies/1/projects?page=1&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Create Project
- **Method**: `POST`
- **URL**: `/api/companies/{company_id}/projects`
- **Description**: Create a new project for a company
- **Auth Required**: Yes

#### Path Parameters
```
company_id: int (required) - ID of the parent company
```

#### Parameters (Body)
```json
{
  "name": "string (required, 1-255 chars) - Project name",
  "status": "string (optional) - Project status (default: ACTIVE)"
}
```

#### Response (Success)
```json
{
  "id": "string - Project ID",
  "name": "string - Project name",
  "status": "string - Project status",
  "company_id": "string - Company ID",
  "ar_content_count": "int - Number of AR content items",
  "created_at": "datetime - Creation timestamp"
}
```

#### Examples
```curl
curl -X POST "http://localhost:8000/api/companies/1/projects" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "name": "Summer Campaign",
    "status": "ACTIVE"
  }'
```

### Get Project
- **Method**: `GET`
- **URL**: `/api/companies/{company_id}/projects/{project_id}`
- **Description**: Retrieve a specific project
- **Auth Required**: Yes

#### Path Parameters
```
company_id: int (required) - ID of the parent company
project_id: int (required) - ID of the project
```

#### Response (Success)
```json
{
  "id": "string - Project ID",
  "name": "string - Project name",
  "status": "string - Project status",
  "company_id": "string - Company ID",
  "ar_content_count": "int - Number of AR content items",
  "created_at": "datetime - Creation timestamp"
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/companies/1/projects/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Update Project
- **Method**: `PUT`
- **URL**: `/api/companies/{company_id}/projects/{project_id}`
- **Description**: Update an existing project
- **Auth Required**: Yes

#### Path Parameters
```
company_id: int (required) - ID of the parent company
project_id: int (required) - ID of the project to update
```

#### Parameters (Body)
```json
{
  "name": "string (optional, 1-255 chars) - Project name",
  "status": "string (optional) - Project status"
}
```

#### Response (Success)
```json
{
  "id": "string - Project ID",
  "name": "string - Project name",
  "status": "string - Project status",
  "company_id": "string - Company ID",
  "ar_content_count": "int - Number of AR content items",
  "created_at": "datetime - Creation timestamp"
}
```

#### Examples
```curl
curl -X PUT "http://localhost:8000/api/companies/1/projects/1" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "name": "Winter Campaign",
    "status": "INACTIVE"
  }'
```

### Delete Project
- **Method**: `DELETE`
- **URL**: `/api/companies/{company_id}/projects/{project_id}`
- **Description**: Delete a project
- **Auth Required**: Yes

#### Path Parameters
```
company_id: int (required) - ID of the parent company
project_id: int (required) - ID of the project to delete
```

#### Response
- 200: Project deleted successfully

#### Examples
```curl
curl -X DELETE "http://localhost:8000/api/companies/1/projects/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## AR Content

### List All AR Content
- **Method**: `GET`
- **URL**: `/api/ar-content`
- **Description**: Retrieve paginated list of all AR content
- **Auth Required**: Yes

#### Query Parameters
```
page: int (optional, default: 1) - Page number
limit: int (optional, default: 10) - Items per page
search: string (optional) - Search term for customer name or project
sort: string (optional) - Sort field (order_number, created_at, views_count)
order: string (optional, default: desc) - Sort order (asc, desc)
```

#### Response (Success)
```json
{
  "items": [
    {
      "id": "int - AR content ID",
      "order_number": "string - Order number",
      "project_id": "int - Project ID",
      "company_id": "int - Company ID",
      "customer_name": "string - Customer name",
      "customer_phone": "string - Customer phone",
      "customer_email": "string - Customer email",
      "duration_years": "int - Duration in years (1, 3, or 5)",
      "views_count": "int - View count",
      "status": "string - Status",
      "active_video_id": "int - Active video ID",
      "public_link": "string - Public link to AR content",
      "qr_code_url": "string - QR code image URL",
      "photo_url": "string - Photo URL",
      "video_url": "string - Video URL",
      "created_at": "datetime - Creation timestamp",
      "updated_at": "datetime - Update timestamp"
    }
  ],
  "total": "int - Total number of items",
  "page": "int - Current page",
  "limit": "int - Items per page",
  "has_more": "bool - Whether there are more pages"
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/ar-content?page=1&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### List AR Content for Project
- **Method**: `GET`
- **URL**: `/api/companies/{company_id}/projects/{project_id}/ar-content`
- **Description**: Retrieve AR content for a specific project
- **Auth Required**: Yes

#### Path Parameters
```
company_id: int (required) - ID of the company
project_id: int (required) - ID of the project
```

#### Response (Success)
```json
{
  "items": [
    {
      "id": "int - AR content ID",
      "order_number": "string - Order number",
      "project_id": "int - Project ID",
      "company_id": "int - Company ID",
      "customer_name": "string - Customer name",
      "customer_phone": "string - Customer phone",
      "customer_email": "string - Customer email",
      "duration_years": "int - Duration in years (1, 3, or 5)",
      "views_count": "int - View count",
      "status": "string - Status",
      "active_video_id": "int - Active video ID",
      "public_link": "string - Public link to AR content",
      "qr_code_url": "string - QR code image URL",
      "photo_url": "string - Photo URL",
      "video_url": "string - Video URL",
      "created_at": "datetime - Creation timestamp",
      "updated_at": "datetime - Update timestamp"
    }
  ]
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/companies/1/projects/1/ar-content" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Create AR Content
- **Method**: `POST`
- **URL**: `/api/ar-content`
- **Description**: Create new AR content with photo and video files
- **Auth Required**: Yes

#### Parameters (Body)
```json
{
  "project_id": "int (required) - Project ID to associate with",
  "customer_name": "string (optional) - Customer name",
  "customer_phone": "string (optional) - Customer phone number",
  "customer_email": "string (optional) - Customer email address",
  "duration_years": "int (optional, default: 1) - Duration in years (1, 3, or 5)"
}
```

#### Response (Success)
```json
{
  "id": "int - AR content ID",
  "order_number": "string - Generated order number",
  "public_link": "string - Public link to AR content",
  "qr_code_url": "string - QR code image URL",
  "photo_url": "string - Photo URL",
  "video_url": "string - Video URL"
}
```

#### Examples
```curl
curl -X POST "http://localhost:8000/api/ar-content" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "project_id": 1,
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "duration_years": 3
  }'
```

### Get AR Content
- **Method**: `GET`
- **URL**: `/api/companies/{company_id}/projects/{project_id}/ar-content/{content_id}`
- **Description**: Retrieve specific AR content with associated videos
- **Auth Required**: Yes

#### Path Parameters
```
company_id: int (required) - ID of the company
project_id: int (required) - ID of the project
content_id: int (required) - ID of the AR content
```

#### Response (Success)
```json
{
  "id": "int - AR content ID",
  "order_number": "string - Order number",
  "public_link": "string - Public link to AR content",
  "qr_code_url": "string - QR code image URL",
  "photo_url": "string - Photo URL",
  "video_url": "string - Video URL",
  "views_count": "int - View count",
  "status": "string - Status",
  "videos": [
    {
      "id": "int - Video ID",
      "ar_content_id": "int - AR content ID",
      "filename": "string - Video filename",
      "duration": "int - Video duration in seconds",
      "size": "int - File size in bytes",
      "video_status": "string - Processing status",
      "is_active": "bool - Whether this is the active video",
      "created_at": "datetime - Creation timestamp"
    }
  ],
  "active_video": {
    "id": "int - Video ID",
    "ar_content_id": "int - AR content ID",
    "filename": "string - Video filename",
    "duration": "int - Video duration in seconds",
    "size": "int - File size in bytes",
    "video_status": "string - Processing status",
    "is_active": "bool - Whether this is the active video",
    "created_at": "datetime - Creation timestamp"
  }
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/companies/1/projects/1/ar-content/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Get AR Content by ID
- **Method**: `GET`
- **URL**: `/api/ar-content/{content_id}`
- **Description**: Retrieve AR content by ID (public endpoint)
- **Auth Required**: No

#### Path Parameters
```
content_id: int (required) - ID of the AR content
```

#### Response (Success)
```json
{
  "id": "int - AR content ID",
  "order_number": "string - Order number",
  "public_link": "string - Public link to AR content",
  "qr_code_url": "string - QR code image URL",
  "photo_url": "string - Photo URL",
  "video_url": "string - Video URL",
  "views_count": "int - View count",
  "status": "string - Status",
  "videos": [
    {
      "id": "int - Video ID",
      "ar_content_id": "int - AR content ID",
      "filename": "string - Video filename",
      "duration": "int - Video duration in seconds",
      "size": "int - File size in bytes",
      "video_status": "string - Processing status",
      "is_active": "bool - Whether this is the active video",
      "created_at": "datetime - Creation timestamp"
    }
  ],
  "active_video": {
    "id": "int - Video ID",
    "ar_content_id": "int - AR content ID",
    "filename": "string - Video filename",
    "duration": "int - Video duration in seconds",
    "size": "int - File size in bytes",
    "video_status": "string - Processing status",
    "is_active": "bool - Whether this is the active video",
    "created_at": "datetime - Creation timestamp"
  }
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/ar-content/1"
```

### Update AR Content
- **Method**: `PUT`
- **URL**: `/api/companies/{company_id}/projects/{project_id}/ar-content/{content_id}`
- **Description**: Update AR content details
- **Auth Required**: Yes

#### Path Parameters
```
company_id: int (required) - ID of the company
project_id: int (required) - ID of the project
content_id: int (required) - ID of the AR content to update
```

#### Parameters (Body)
```json
{
  "customer_name": "string (optional) - Customer name",
  "customer_phone": "string (optional) - Customer phone number",
  "customer_email": "string (optional) - Customer email address",
  "status": "string (optional) - Status",
  "duration_years": "int (optional) - Duration in years (1, 3, or 5)"
}
```

#### Response (Success)
```json
{
  "id": "int - AR content ID",
  "order_number": "string - Order number",
 "project_id": "int - Project ID",
  "company_id": "int - Company ID",
  "customer_name": "string - Customer name",
  "customer_phone": "string - Customer phone",
  "customer_email": "string - Customer email",
  "duration_years": "int - Duration in years (1, 3, or 5)",
  "views_count": "int - View count",
  "status": "string - Status",
  "active_video_id": "int - Active video ID",
  "public_link": "string - Public link to AR content",
  "qr_code_url": "string - QR code image URL",
  "photo_url": "string - Photo URL",
  "video_url": "string - Video URL",
  "created_at": "datetime - Creation timestamp",
  "updated_at": "datetime - Update timestamp"
}
```

#### Examples
```curl
curl -X PUT "http://localhost:8000/api/companies/1/projects/1/ar-content/1" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "customer_name": "Updated John Doe",
    "status": "ACTIVE"
  }'
```

### Update AR Content Video
- **Method**: `PATCH`
- **URL**: `/api/companies/{company_id}/projects/{project_id}/ar-content/{content_id}/video`
- **Description**: Update the active video for AR content
- **Auth Required**: Yes

#### Path Parameters
```
company_id: int (required) - ID of the company
project_id: int (required) - ID of the project
content_id: int (required) - ID of the AR content
```

#### Parameters (Body)
```json
{
  "active_video_id": "int (required) - ID of the video to set as active"
}
```

#### Response (Success)
```json
{
  "id": "int - AR content ID",
  "order_number": "string - Order number",
  "project_id": "int - Project ID",
  "company_id": "int - Company ID",
  "customer_name": "string - Customer name",
  "customer_phone": "string - Customer phone",
  "customer_email": "string - Customer email",
  "duration_years": "int - Duration in years (1, 3, or 5)",
  "views_count": "int - View count",
  "status": "string - Status",
  "active_video_id": "int - Active video ID",
  "public_link": "string - Public link to AR content",
  "qr_code_url": "string - QR code image URL",
  "photo_url": "string - Photo URL",
  "video_url": "string - Video URL",
  "created_at": "datetime - Creation timestamp",
  "updated_at": "datetime - Update timestamp"
}
```

#### Examples
```curl
curl -X PATCH "http://localhost:8000/api/companies/1/projects/1/ar-content/1/video" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "active_video_id": 2
  }'
```

### Delete AR Content
- **Method**: `DELETE`
- **URL**: `/api/companies/{company_id}/projects/{project_id}/ar-content/{content_id}`
- **Description**: Delete AR content and all associated files
- **Auth Required**: Yes

#### Path Parameters
```
company_id: int (required) - ID of the company
project_id: int (required) - ID of the project
content_id: int (required) - ID of the AR content to delete
```

#### Response
- 200: AR content deleted successfully

#### Examples
```curl
curl -X DELETE "http://localhost:8000/api/companies/1/projects/1/ar-content/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Videos

### Upload Videos
- **Method**: `POST`
- **URL**: `/api/ar-content/{content_id}/videos`
- **Description**: Upload videos for AR content (multipart form data)
- **Auth Required**: Yes

#### Path Parameters
```
content_id: int (required) - ID of the AR content
```

#### Parameters (Form Data)
```
files: array of files (required) - Video files to upload
```

#### Response (Success)
```json
{
  "message": "string - Success message",
  "uploaded_files": [
    {
      "id": "int - Video ID",
      "filename": "string - Uploaded filename",
      "status": "string - Upload status"
    }
  ]
}
```

#### Examples
```curl
curl -X POST "http://localhost:8000/api/ar-content/1/videos" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "files=@video1.mp4" \
  -F "files=@video2.mp4"
```

### List Videos
- **Method**: `GET`
- **URL**: `/api/ar-content/{content_id}/videos`
- **Description**: Get all videos for AR content with computed status and schedule info
- **Auth Required**: Yes

#### Path Parameters
```
content_id: int (required) - ID of the AR content
```

#### Response (Success)
```json
{
  "items": [
    {
      "id": "int - Video ID",
      "ar_content_id": "int - AR content ID",
      "filename": "string - Video filename",
      "duration": "int - Video duration in seconds",
      "size": "int - File size in bytes",
      "video_status": "string - Processing status",
      "is_active": "bool - Whether this is the active video",
      "created_at": "datetime - Creation timestamp",
      "scheduled_dates": "array - Scheduled dates if applicable",
      "subscription_ends_at": "datetime - Subscription end date if applicable"
    }
  ]
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/ar-content/1/videos" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Set Active Video
- **Method**: `PATCH`
- **URL**: `/api/ar-content/{content_id}/videos/{video_id}/set-active`
- **Description**: Atomically set a video as the active one for AR content
- **Auth Required**: Yes

#### Path Parameters
```
content_id: int (required) - ID of the AR content
video_id: int (required) - ID of the video to activate
```

#### Response (Success)
```json
{
  "message": "string - Success message",
  "previous_active_video_id": "int - ID of previously active video",
  "new_active_video_id": "int - ID of newly activated video"
}
```

#### Examples
```curl
curl -X PATCH "http://localhost:8000/api/ar-content/1/videos/2/set-active" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Update Video Subscription
- **Method**: `PATCH`
- **URL**: `/api/ar-content/{content_id}/videos/{video_id}/subscription`
- **Description**: Update video subscription end date
- **Auth Required**: Yes

#### Path Parameters
```
content_id: int (required) - ID of the AR content
video_id: int (required) - ID of the video
```

#### Parameters (Body)
```json
{
  "subscription_end_date": "string (required) - New subscription end date (YYYY-MM-DD)"
}
```

#### Response (Success)
```json
{
  "message": "string - Success message",
  "video_id": "int - Video ID",
  "subscription_ends_at": "datetime - New subscription end date"
}
```

#### Examples
```curl
curl -X PATCH "http://localhost:8000/api/ar-content/1/videos/2/subscription" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "subscription_end_date": "2024-12-31"
  }'
```

### Update Video Rotation
- **Method**: `PATCH`
- **URL**: `/api/ar-content/{content_id}/videos/{video_id}/rotation`
- **Description**: Update video rotation type and reset rotation state
- **Auth Required**: Yes

#### Path Parameters
```
content_id: int (required) - ID of the AR content
video_id: int (required) - ID of the video
```

#### Parameters (Body)
```json
{
  "rotation_type": "string (required) - Rotation type (none, sequential, cyclic)"
}
```

#### Response (Success)
```json
{
  "status": "updated",
  "rotation_type": "string - New rotation type",
  "rotation_state": "int - Current rotation state (reset to 0)",
  "message": "string - Success message"
}
```

#### Examples
```curl
curl -X PATCH "http://localhost:8000/api/ar-content/1/videos/2/rotation" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "rotation_type": "cyclic"
  }'
```

### Update Playback Mode
- **Method**: `PATCH`
- **URL**: `/api/videos/ar-content/{content_id}/playback-mode`
- **Description**: Switch playback mode between manual and automatic rotation (sequential/cyclic)
- **Auth Required**: Yes

#### Path Parameters
```
content_id: int (required) - ID of the AR content
```

#### Parameters (Body)

For manual mode:
```json
{
  "mode": "manual",
  "active_video_id": "int (required) - ID of the video to set as active"
}
```

For automatic modes (sequential/cyclic):
```json
{
  "mode": "sequential" | "cyclic",
  "active_video_ids": "array of ints (required) - IDs of videos to include in rotation"
}
```

#### Response (Success)
```json
{
  "status": "updated",
  "mode": "string - Playback mode (manual, sequential, cyclic)",
  "active_video_id": "int | null - Active video ID (for manual mode)",
  "active_video_ids": "array of ints - Active video IDs (for automatic modes)"
}
```

#### Examples

Manual mode:
```curl
curl -X PATCH "http://localhost:8000/api/videos/ar-content/1/playback-mode" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "mode": "manual",
    "active_video_id": 2
  }'
```

Sequential mode:
```curl
curl -X PATCH "http://localhost:8000/api/videos/ar-content/1/playback-mode" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "mode": "sequential",
    "active_video_ids": [1, 2, 3]
  }'
```

Cyclic mode:
```curl
curl -X PATCH "http://localhost:8000/api/videos/ar-content/1/playback-mode" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "mode": "cyclic",
    "active_video_ids": [1, 2, 3]
  }'
```

#### Playback Modes Description

- **manual**: One fixed video. User selects the active video manually. No automatic rotation.
- **sequential**: Videos switch sequentially (1→2→3→...→last). Stops at the last video. Rotation state increments after each video ends.
- **cyclic**: Videos switch cyclically (1→2→3→...→1→2→...). Wraps around after the last video. Rotation state increments and wraps around.

**Note**: In AR viewer, videos automatically switch to the next one after the current video ends (based on `rotation_state`). The rotation state is updated each time the viewer requests the active video.

### List Video Schedules
- **Method**: `GET`
- **URL**: `/api/ar-content/{content_id}/videos/{video_id}/schedules`
- **Description**: Get all schedules for a video
- **Auth Required**: Yes

#### Path Parameters
```
content_id: int (required) - ID of the AR content
video_id: int (required) - ID of the video
```

#### Response (Success)
```json
{
  "items": [
    {
      "id": "int - Schedule ID",
      "video_id": "int - Video ID",
      "date": "string - Scheduled date (YYYY-MM-DD)",
      "start_time": "string - Start time (HH:MM)",
      "end_time": "string - End time (HH:MM)",
      "is_active": "bool - Whether schedule is active"
    }
  ]
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/ar-content/1/videos/2/schedules" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Create Video Schedule
- **Method**: `POST`
- **URL**: `/api/ar-content/{content_id}/videos/{video_id}/schedules`
- **Description**: Create a new schedule for a video
- **Auth Required**: Yes

#### Path Parameters
```
content_id: int (required) - ID of the AR content
video_id: int (required) - ID of the video
```

#### Parameters (Body)
```json
{
  "date": "string (required) - Scheduled date (YYYY-MM-DD)",
  "start_time": "string (required) - Start time (HH:MM)",
  "end_time": "string (required) - End time (HH:MM)",
  "is_active": "bool (optional, default: true) - Whether schedule is active"
}
```

#### Response (Success)
```json
{
  "id": "int - Schedule ID",
  "video_id": "int - Video ID",
  "date": "string - Scheduled date (YYYY-MM-DD)",
  "start_time": "string - Start time (HH:MM)",
  "end_time": "string - End time (HH:MM)",
  "is_active": "bool - Whether schedule is active"
}
```

#### Examples
```curl
curl -X POST "http://localhost:8000/api/ar-content/1/videos/2/schedules" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "date": "2024-01-15",
    "start_time": "09:00",
    "end_time": "17:00",
    "is_active": true
  }'
```

### Update Video Schedule
- **Method**: `PATCH`
- **URL**: `/api/ar-content/{content_id}/videos/{video_id}/schedules/{schedule_id}`
- **Description**: Update an existing schedule
- **Auth Required**: Yes

#### Path Parameters
```
content_id: int (required) - ID of the AR content
video_id: int (required) - ID of the video
schedule_id: int (required) - ID of the schedule to update
```

#### Parameters (Body)
```json
{
  "date": "string (optional) - Scheduled date (YYYY-MM-DD)",
  "start_time": "string (optional) - Start time (HH:MM)",
  "end_time": "string (optional) - End time (HH:MM)",
  "is_active": "bool (optional) - Whether schedule is active"
}
```

#### Response (Success)
```json
{
  "id": "int - Schedule ID",
  "video_id": "int - Video ID",
  "date": "string - Scheduled date (YYYY-MM-DD)",
  "start_time": "string - Start time (HH:MM)",
  "end_time": "string - End time (HH:MM)",
  "is_active": "bool - Whether schedule is active"
}
```

#### Examples
```curl
curl -X PATCH "http://localhost:8000/api/ar-content/1/videos/2/schedules/1" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "start_time": "10:00",
    "end_time": "18:00"
  }'
```

### Delete Video Schedule
- **Method**: `DELETE`
- **URL**: `/api/ar-content/{content_id}/videos/{video_id}/schedules/{schedule_id}`
- **Description**: Delete a schedule
- **Auth Required**: Yes

#### Path Parameters
```
content_id: int (required) - ID of the AR content
video_id: int (required) - ID of the video
schedule_id: int (required) - ID of the schedule to delete
```

#### Response
- 200: Schedule deleted successfully

#### Examples
```curl
curl -X DELETE "http://localhost:8000/api/ar-content/1/videos/2/schedules/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Update Video
- **Method**: `PUT`
- **URL**: `/api/videos/{video_id}`
- **Description**: Legacy endpoint - use specific PATCH endpoints instead
- **Auth Required**: Yes

#### Path Parameters
```
video_id: string (required) - ID of the video to update
```

#### Parameters (Body)
```json
{
  "filename": "string (optional) - New filename",
  "is_active": "bool (optional) - Whether video is active"
}
```

#### Response (Success)
```json
{
  "message": "string - Success message",
  "video_id": "string - Updated video ID"
}
```

#### Examples
```curl
curl -X PUT "http://localhost:8000/api/videos/2" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "is_active": true
  }'
```

### Delete Video
- **Method**: `DELETE`
- **URL**: `/api/videos/{video_id}`
- **Description**: Delete a video and all its schedules
- **Auth Required**: Yes

#### Path Parameters
```
video_id: string (required) - ID of the video to delete
```

#### Response
- 200: Video deleted successfully

#### Examples
```curl
curl -X DELETE "http://localhost:8000/api/videos/2" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Analytics

### Analytics Overview
- **Method**: `GET`
- **URL**: `/api/analytics/overview`
- **Description**: Get platform-wide analytics overview
- **Auth Required**: Yes

#### Response (Success)
```json
{
  "total_companies": "int - Total number of companies",
  "total_projects": "int - Total number of projects",
  "total_ar_content": "int - Total number of AR content items",
  "total_views": "int - Total number of views",
  "recent_activity": [
    {
      "date": "string - Date (YYYY-MM-DD)",
      "views": "int - Number of views",
      "new_content": "int - Number of new AR content created"
    }
  ]
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/analytics/overview" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Company Analytics
- **Method**: `GET`
- **URL**: `/api/analytics/companies/{company_id}`
- **Description**: Get analytics for a specific company
- **Auth Required**: Yes

#### Path Parameters
```
company_id: int (required) - ID of the company
```

#### Response (Success)
```json
{
  "company_id": "int - Company ID",
  "name": "string - Company name",
  "projects_count": "int - Number of projects",
  "ar_content_count": "int - Number of AR content items",
  "total_views": "int - Total views",
  "recent_activity": [
    {
      "date": "string - Date (YYYY-MM-DD)",
      "views": "int - Number of views",
      "new_content": "int - Number of new AR content created"
    }
  ]
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/analytics/companies/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Project Analytics
- **Method**: `GET`
- **URL**: `/api/analytics/projects/{project_id}`
- **Description**: Get analytics for a specific project
- **Auth Required**: Yes

#### Path Parameters
```
project_id: int (required) - ID of the project
```

#### Response (Success)
```json
{
  "project_id": "int - Project ID",
  "name": "string - Project name",
  "ar_content_count": "int - Number of AR content items",
  "total_views": "int - Total views",
  "recent_activity": [
    {
      "date": "string - Date (YYYY-MM-DD)",
      "views": "int - Number of views",
      "new_content": "int - Number of new AR content created"
    }
  ]
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/analytics/projects/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### AR Content Analytics
- **Method**: `GET`
- **URL**: `/api/analytics/ar-content/{content_id}`
- **Description**: Get analytics for a specific AR content
- **Auth Required**: Yes

#### Path Parameters
```
content_id: int (required) - ID of the AR content
```

#### Response (Success)
```json
{
  "content_id": "int - AR content ID",
  "order_number": "string - Order number",
  "views_count": "int - Total views",
  "unique_visitors": "int - Unique visitors count",
  "view_duration_avg": "float - Average view duration in seconds",
  "recent_views": [
    {
      "date": "string - Date (YYYY-MM-DD)",
      "count": "int - Number of views on that day"
    }
  ]
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/analytics/ar-content/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Track AR Session
- **Method**: `POST`
- **URL**: `/api/analytics/ar-session`
- **Description**: Track AR session analytics (legacy endpoint)
- **Auth Required**: Yes

#### Parameters (Body)
```json
{
  "content_id": "int (required) - AR content ID",
  "session_id": "string (required) - Unique session identifier",
  "duration": "int (optional) - Session duration in seconds",
  "actions": "array (optional) - List of user actions during session"
}
```

#### Response (Success)
```json
{
  "message": "string - Success message",
  "session_id": "string - Tracked session ID"
}
```

#### Examples
```curl
curl -X POST "http://localhost:8000/api/analytics/ar-session" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "content_id": 1,
    "session_id": "session-12345",
    "duration": 120,
    "actions": ["marker_detected", "video_played", "exit"]
  }'
```

### Mobile Session Start
- **Method**: `POST`
- **URL**: `/api/mobile/sessions`
- **Description**: Create AR mobile/browser session (minimal REST)
- **Auth Required**: No

#### Parameters (Body)
```json
{
  "content_id": "int (required) - AR content ID",
  "device_id": "string (required) - Device identifier",
  "platform": "string (optional) - Platform (ios, android, web)",
  "session_type": "string (optional) - Session type (mobile, browser)"
}
```

#### Response (Success)
```json
{
  "session_id": "string - Created session ID",
  "content_id": "int - AR content ID",
  "expires_at": "datetime - Session expiration timestamp"
}
```

#### Examples
```curl
curl -X POST "http://localhost:8000/api/mobile/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "content_id": 1,
    "device_id": "device-12345",
    "platform": "web"
  }'
```

### Mobile Analytics Update
- **Method**: `POST`
- **URL**: `/api/mobile/analytics`
- **Description**: Update session analytics (minimal REST)
- **Auth Required**: No

#### Parameters (Body)
```json
{
  "session_id": "string (required) - Session identifier",
  "content_id": "int (required) - AR content ID",
 "event_type": "string (required) - Event type (view_start, marker_detected, video_played, view_end)",
  "duration": "int (optional) - Duration in seconds",
  "data": "object (optional) - Additional event data"
}
```

#### Response (Success)
```json
{
  "message": "string - Success message",
  "event_processed": "bool - Whether event was processed"
}
```

#### Examples
```curl
curl -X POST "http://localhost:8000/api/mobile/analytics" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-12345",
    "content_id": 1,
    "event_type": "video_played",
    "duration": 30,
    "data": {
      "video_id": 2
    }
  }'
```

---

## Notifications

### List Notifications
- **Method**: `GET`
- **URL**: `/api/notifications`
- **Description**: Get paginated list of notifications
- **Auth Required**: Yes

#### Query Parameters
```
page: int (optional, default: 1) - Page number
limit: int (optional, default: 10) - Items per page
unread_only: bool (optional, default: false) - Only return unread notifications
```

#### Response (Success)
```json
{
  "items": [
    {
      "id": "int - Notification ID",
      "title": "string - Notification title",
      "message": "string - Notification message",
      "type": "string - Notification type",
      "is_read": "bool - Whether notification has been read",
      "created_at": "datetime - Creation timestamp"
    }
  ],
  "total": "int - Total number of notifications",
  "page": "int - Current page",
  "limit": "int - Items per page",
  "has_more": "bool - Whether there are more pages"
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/notifications?page=1&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Mark Notifications Read
- **Method**: `POST`
- **URL**: `/api/notifications/mark-read`
- **Description**: Mark notifications as read
- **Auth Required**: Yes

#### Parameters (Body)
```json
{
  "notification_ids": "array of ints (optional) - Specific notification IDs to mark as read",
  "all": "bool (optional) - Mark all notifications as read (default: false)"
}
```

#### Response (Success)
```json
{
  "message": "string - Success message",
  "updated_count": "int - Number of notifications updated"
}
```

#### Examples
```curl
curl -X POST "http://localhost:8000/api/notifications/mark-read" \
 -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "notification_ids": [1, 2, 3]
  }'
```

### Delete Notification
- **Method**: `DELETE`
- **URL**: `/api/notifications/{notification_id}`
- **Description**: Delete a notification
- **Auth Required**: Yes

#### Path Parameters
```
notification_id: int (required) - ID of the notification to delete
```

#### Response
- 200: Notification deleted successfully

#### Examples
```curl
curl -X DELETE "http://localhost:8000/api/notifications/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Test Notification
- **Method**: `POST`
- **URL**: `/api/notifications/test`
- **Description**: Send a test notification
- **Auth Required**: Yes

#### Parameters (Query)
```
email: string (required) - Email address to send notification to
chat_id: string (required) - Chat ID for Telegram notification
```

#### Response
- 20: Test notification sent successfully

#### Examples
```curl
curl -X POST "http://localhost:8000/api/notifications/test?email=test@example.com&chat_id=123456" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Storage

### Create Storage Connection
- **Method**: `POST`
- **URL**: `/api/storage/connections`
- **Description**: Create a new storage connection
- **Auth Required**: Yes

#### Parameters (Body)
```json
{
  "name": "string (required) - Connection name",
  "type": "string (required) - Storage type (local, s3, yandex)",
  "config": "object (required) - Connection configuration"
}
```

#### Response (Success)
```json
{
  "id": "int - Connection ID",
  "name": "string - Connection name",
  "type": "string - Storage type",
  "created_at": "datetime - Creation timestamp"
}
```

#### Examples
```curl
curl -X POST "http://localhost:8000/api/storage/connections" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "name": "My S3 Storage",
    "type": "s3",
    "config": {
      "endpoint": "https://s3.amazonaws.com",
      "bucket": "my-bucket",
      "access_key": "access-key",
      "secret_key": "secret-key"
    }
  }'
```

### Test Storage Connection
- **Method**: `POST`
- **URL**: `/api/storage/connections/{connection_id}/test`
- **Description**: Test a storage connection
- **Auth Required**: Yes

#### Path Parameters
```
connection_id: int (required) - ID of the storage connection
```

#### Response (Success)
```json
{
  "message": "string - Test result message",
  "success": "bool - Whether test was successful"
}
```

#### Examples
```curl
curl -X POST "http://localhost:8000/api/storage/connections/1/test" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Get Storage Stats
- **Method**: `GET`
- **URL**: `/api/storage/connections/{connection_id}/stats`
- **Description**: Get storage statistics
- **Auth Required**: Yes

#### Path Parameters
```
connection_id: int (required) - ID of the storage connection
```

#### Query Parameters
```
path: string (optional, default: "") - Path to get stats for
```

#### Response (Success)
```json
{
  "total_size": "int - Total size in bytes",
  "file_count": "int - Number of files",
  "used_space": "int - Used space in bytes",
  "available_space": "int - Available space in bytes"
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/storage/connections/1/stats" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Set Company Storage
- **Method**: `PUT`
- **URL**: `/api/companies/{company_id}/storage`
- **Description**: Set storage connection for a company
- **Auth Required**: Yes

#### Path Parameters
```
company_id: int (required) - ID of the company
```

#### Parameters (Body)
```json
{
  "storage_connection_id": "int (required) - ID of the storage connection to use"
}
```

#### Response (Success)
```json
{
  "message": "string - Success message",
  "company_id": "int - Company ID",
  "storage_connection_id": "int - Storage connection ID"
}
```

#### Examples
```curl
curl -X PUT "http://localhost:8000/api/companies/1/storage" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "storage_connection_id": 1
  }'
```

### List Storage Connections
- **Method**: `GET`
- **URL**: `/api/storage/connections`
- **Description**: Get list of all storage connections
- **Auth Required**: Yes

#### Response (Success)
```json
{
  "items": [
    {
      "id": "int - Connection ID",
      "name": "string - Connection name",
      "type": "string - Storage type",
      "created_at": "datetime - Creation timestamp"
    }
  ]
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/storage/connections" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Rotation

### Set Rotation
- **Method**: `POST`
- **URL**: `/api/rotation/ar-content/{content_id}/rotation`
- **Description**: Set rotation schedule for AR content
- **Auth Required**: Yes

#### Path Parameters
```
content_id: int (required) - ID of the AR content
```

#### Parameters (Body)
```json
{
  "rotation_type": "string (required) - Rotation type (DAILY, WEEKLY, MONTHLY, CUSTOM)",
  "schedule": "object (required) - Rotation schedule configuration"
}
```

#### Response (Success)
```json
{
  "message": "string - Success message",
  "content_id": "int - AR content ID",
  "rotation_type": "string - Rotation type"
}
```

#### Examples
```curl
curl -X POST "http://localhost:8000/api/rotation/ar-content/1/rotation" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "rotation_type": "WEEKLY",
    "schedule": {
      "monday": {"start_time": "09:00", "end_time": "17:00"},
      "tuesday": {"start_time": "09:00", "end_time": "17:00"}
    }
  }'
```

### Update Rotation
- **Method**: `PUT`
- **URL**: `/api/rotation/{schedule_id}`
- **Description**: Update an existing rotation schedule
- **Auth Required**: Yes

#### Path Parameters
```
schedule_id: int (required) - ID of the rotation schedule
```

#### Parameters (Body)
```json
{
  "rotation_type": "string (optional) - Rotation type (DAILY, WEEKLY, MONTHLY, CUSTOM)",
  "schedule": "object (optional) - Rotation schedule configuration"
}
```

#### Response (Success)
```json
{
  "message": "string - Success message",
  "schedule_id": "int - Schedule ID",
  "rotation_type": "string - Rotation type"
}
```

#### Examples
```curl
curl -X PUT "http://localhost:8000/api/rotation/1" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "rotation_type": "DAILY",
    "schedule": {
      "start_time": "10:00",
      "end_time": "18:00"
    }
  }'
```

### Delete Rotation
- **Method**: `DELETE`
- **URL**: `/api/rotation/{schedule_id}`
- **Description**: Delete a rotation schedule
- **Auth Required**: Yes

#### Path Parameters
```
schedule_id: int (required) - ID of the rotation schedule to delete
```

#### Response
- 200: Rotation schedule deleted successfully

#### Examples
```curl
curl -X DELETE "http://localhost:8000/api/rotation/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Set Rotation Sequence
- **Method**: `POST`
- **URL**: `/api/rotation/ar-content/{content_id}/rotation/sequence`
- **Description**: Set rotation sequence for AR content
- **Auth Required**: Yes

#### Path Parameters
```
content_id: int (required) - ID of the AR content
```

#### Parameters (Body)
```json
{
  "video_ids": "array of ints (required) - Ordered list of video IDs for rotation"
}
```

#### Response (Success)
```json
{
  "message": "string - Success message",
  "content_id": "int - AR content ID",
  "video_ids": "array of ints - Ordered video IDs"
}
```

#### Examples
```curl
curl -X POST "http://localhost:8000/api/rotation/ar-content/1/rotation/sequence" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "video_ids": [1, 2, 3]
  }'
```

### Rotation Calendar
- **Method**: `GET`
- **URL**: `/api/rotation/ar-content/{content_id}/rotation/calendar`
- **Description**: Get a calendar of planned videos for a given month
- **Auth Required**: Yes

#### Path Parameters
```
content_id: int (required) - ID of the AR content
```

#### Query Parameters
```
month: string (required) - Month in YYYY-MM format
```

#### Response (Success)
```json
{
  "month": "string - Month in YYYY-MM format",
  "calendar": {
    "day_1": {
      "video_id": "int - Video ID for day 1",
      "video_title": "string - Video title"
    },
    "day_2": {
      "video_id": "int - Video ID for day 2",
      "video_title": "string - Video title"
    }
    // ... and so on for each day of the month
  }
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/rotation/ar-content/1/rotation/calendar?month=2024-01" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## OAuth

### Initiate Yandex OAuth
- **Method**: `GET`
- **URL**: `/api/oauth/authorize`
- **Description**: Initiate Yandex OAuth flow
- **Auth Required**: Yes

#### Query Parameters
```
redirect_uri: string (required) - URI to redirect after OAuth completion
state: string (optional) - State parameter for security
```

#### Response (Success)
```json
{
  "authorization_url": "string - URL to redirect user for OAuth",
  "state": "string - State parameter for verification"
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/oauth/authorize?redirect_uri=http://localhost:3000/oauth/callback" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Yandex OAuth Callback
- **Method**: `GET`
- **URL**: `/api/oauth/callback`
- **Description**: Handle Yandex OAuth callback
- **Auth Required**: Yes

#### Query Parameters
```
code: string (required) - OAuth code from Yandex
state: string (required) - State parameter for verification
```

#### Response (Success)
```json
{
  "message": "string - Success message",
  "connection_id": "int - Created connection ID",
  "expires_in": "int - Token expiry in seconds"
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/oauth/callback?code=oauth-code&state=state-value" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### List Yandex Folders
- **Method**: `GET`
- **URL**: `/api/oauth/{connection_id}/folders`
- **Description**: List folders from Yandex Disk connection
- **Auth Required**: Yes

#### Path Parameters
```
connection_id: int (required) - ID of the Yandex connection
```

#### Query Parameters
```
path: string (optional, default: "/") - Path to list folders from
```

#### Response (Success)
```json
{
  "items": [
    {
      "id": "string - Folder ID",
      "name": "string - Folder name",
      "path": "string - Full path",
      "modified": "datetime - Last modification date",
      "size": "int - Size in bytes"
    }
  ],
  "current_path": "string - Current path",
  "parent_path": "string - Parent path"
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/oauth/1/folders" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Create Yandex Folder
- **Method**: `POST`
- **URL**: `/api/oauth/{connection_id}/create-folder`
- **Description**: Create a folder in Yandex Disk
- **Auth Required**: Yes

#### Path Parameters
```
connection_id: int (required) - ID of the Yandex connection
```

#### Parameters (Body)
```json
{
  "folder_name": "string (required) - Name of the folder to create",
  "parent_path": "string (optional, default: "/") - Parent path for the new folder"
}
```

#### Response (Success)
```json
{
  "message": "string - Success message",
  "folder_path": "string - Full path to created folder"
}
```

#### Examples
```curl
curl -X POST "http://localhost:8000/api/oauth/1/create-folder" \
 -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "folder_name": "New Folder",
    "parent_path": "/AR Content"
  }'
```

---

## Public

### Get Public AR Content
- **Method**: `GET`
- **URL**: `/api/public/ar/{unique_id}/content`
- **Description**: Get public AR content by unique ID
- **Auth Required**: No

#### Path Parameters
```
unique_id: string (required) - Unique identifier for AR content
```

#### Response (Success)
```json
{
  "id": "int - AR content ID",
  "order_number": "string - Order number",
  "public_link": "string - Public link to AR content",
  "qr_code_url": "string - QR code image URL",
  "photo_url": "string - Photo URL",
  "video_url": "string - Video URL",
  "views_count": "int - View count",
  "status": "string - Status",
  "videos": [
    {
      "id": "int - Video ID",
      "ar_content_id": "int - AR content ID",
      "filename": "string - Video filename",
      "duration": "int - Video duration in seconds",
      "size": "int - File size in bytes",
      "video_status": "string - Processing status",
      "is_active": "bool - Whether this is the active video",
      "created_at": "datetime - Creation timestamp"
    }
  ],
  "active_video": {
    "id": "int - Video ID",
    "ar_content_id": "int - AR content ID",
    "filename": "string - Video filename",
    "duration": "int - Video duration in seconds",
    "size": "int - File size in bytes",
    "video_status": "string - Processing status",
    "is_active": "bool - Whether this is the active video",
    "created_at": "datetime - Creation timestamp"
  }
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/public/ar/unique-id/content"
```

### Get Public AR Content Redirect
- **Method**: `GET`
- **URL**: `/api/public/ar-content/{unique_id}`
- **Description**: Redirect to public AR content page
- **Auth Required**: No

#### Path Parameters
```
unique_id: string (required) - Unique identifier for AR content
```

#### Response
- 302: Redirect to public AR content page

#### Examples
```curl
curl -X GET "http://localhost:8000/api/public/ar-content/unique-id"
```

---

## Viewer

### Viewer API contract (Android)

Эндпоинты Viewer используются приложением в каталоге **android/** (AR Viewer). При изменении бэкенда:

- **Не ломайте контракт без смены версии:** поля ответа манифеста (`manifest_version`, `marker_image_url`, `video`, `expires_at`, `status` и вложенный объект `video`) должны оставаться обратно совместимыми или сопровождаться увеличением `manifest_version` и обновлением приложения.
- **Проверяйте сборку Android после правок API:** в CI при пуше в `android/` запускается сборка; при изменении Viewer API убедитесь, что приложение по-прежнему собирается и совместимо с новым контрактом (при необходимости обновите клиент в `android/` и версию манифеста).

Список эндпоинтов контракта: манифест (`GET /api/viewer/ar/{unique_id}/manifest`), проверка доступности (`GET /api/viewer/ar/{unique_id}/check`), активное видео (`GET /api/viewer/ar/{unique_id}/active-video`), App Links (`GET /.well-known/assetlinks.json`). Полное описание ответов и кодов ошибок — в подразделах ниже.

**Версионирование манифеста:** поле `manifest_version` в теле ответа (и опционально заголовок `X-Manifest-Version`) задаёт версию контракта. При внесении несовместимых изменений (удаление или переименование полей, смена типов) необходимо увеличить версию и обновить клиент. Добавление новых опциональных полей допускается без смены версии.

---

### Viewer Manifest API (ARCore app)

Single endpoint used by the Android AR Viewer app to load AR content by `unique_id`. Returns the tracking image URL (marker = photo, raster JPEG/PNG; the .mind format is not used), active video, and metadata. Each successful call increments the view counter.

- **Method**: `GET`
- **URL**: `/api/viewer/ar/{unique_id}/manifest`
- **Description**: Get viewer manifest for Android ARCore app. Returns marker image URL (photo for tracking), active video, subscription expiry, status. Increments `views_count` for the AR content.
- **Auth Required**: No

#### Path Parameters
```
unique_id: string (required) - UUID of the AR content (e.g. from /view/{unique_id} or QR link)
```

#### Response (Success 200)
```json
{
  "manifest_version": "1",
  "unique_id": "550e8400-e29b-41d4-a716-446655440000",
  "order_number": "AR-001",
  "marker_image_url": "https://your-domain.com/storage/ar_content/.../main_image.jpg",
  "photo_url": "https://your-domain.com/storage/ar_content/.../main_image.jpg",
  "video": {
    "id": 1,
    "title": "video.mp4",
    "video_url": "https://your-domain.com/storage/.../video.mp4",
    "thumbnail_url": "https://your-domain.com/...",
    "duration": 120,
    "width": 1920,
    "height": 1080,
    "mime_type": "video/mp4",
    "selection_source": "schedule",
    "schedule_id": 1,
    "expires_in_days": 365,
    "selected_at": "2025-02-03T12:00:00.000000+00:00"
  },
  "expires_at": "2026-02-03T00:00:00",
  "status": "ready"
}
```

| Field | Type | Description |
|-------|------|-------------|
| manifest_version | string | API version of the manifest (e.g. "1"); bump when breaking changes are introduced. |
| unique_id | string | Same as path parameter. |
| order_number | string | Human-readable order/project identifier. |
| marker_image_url | string | Absolute URL of the photo image (raster JPEG/PNG) used as AR tracking target (ARCore). The .mind format is not used. |
| photo_url | string | Same as marker_image_url (legacy). |
| video | object | Active video selected by scheduler (schedule / active_default / rotation / fallback). |
| expires_at | string | ISO datetime when the AR content subscription expires. |
| status | string | Content status, e.g. "ready", "active". |

#### Error Responses
| Code | Detail | Description |
|------|--------|-------------|
| 400 | Invalid unique_id format | `unique_id` is not a valid UUID. |
| 400 | Photo (marker image) not available | No photo uploaded for this AR content. |
| 400 | Marker is still being generated, try again later | `marker_status` is not `ready` (e.g. pending, processing). |
| 400 | AR content is not active or ready | Content status is not suitable for viewing. |
| 400 | No playable videos available for this AR content | No active video could be selected. |
| 403 | AR content subscription has expired | Current date is after `expires_at`. |
| 404 | AR content not found | No AR content with this `unique_id`. |
| 500 | Internal server error | Server-side error. |

#### Examples
```curl
curl -X GET "http://localhost:8000/api/viewer/ar/550e8400-e29b-41d4-a716-446655440000/manifest"
```

**Note**: For sequential/cyclic playback modes, the app can request the next video via `GET /api/viewer/ar/{unique_id}/active-video` without incrementing the view count again (manifest call already increments it once per session).

### Check AR content availability (no view count)
- **Method**: `GET`
- **URL**: `/api/viewer/ar/{unique_id}/check`
- **Description**: Check if AR content is available for viewing without incrementing the view counter. Use to show a message (e.g. "Content unavailable" or "Subscription expired") before fetching the full manifest.
- **Auth Required**: No

#### Response (200)
- `content_available: true` — content is playable.
- `content_available: false`, `reason: string` — one of: `invalid_unique_id`, `not_found`, `subscription_expired`, `content_not_active`, `marker_image_not_available`, `marker_still_generating`, `no_playable_video`.

---

### Get Viewer Active Video
- **Method**: `GET`
- **URL**: `/api/viewer/{ar_content_id}/active-video`
- **Description**: Get the active video for AR content viewer with metadata. Implements video selection logic with priority: scheduled videos → active video → rotation-based selection → fallback. For sequential/cyclic rotation modes, automatically updates rotation state after each request.
- **Auth Required**: No

#### Path Parameters
```
ar_content_id: int (required) - ID of the AR content
```

#### Response (Success)
```json
{
  "id": "int - Video ID",
  "title": "string - Video title",
  "video_url": "string - Video URL",
  "preview_url": "string - Preview URL",
  "thumbnail_url": "string - Thumbnail URL",
  "duration": "int - Video duration in seconds",
  "width": "int - Video width in pixels",
  "height": "int - Video height in pixels",
  "mime_type": "string - Video MIME type",
  "selection_source": "string - Selection source (schedule, active_default, rotation, fallback)",
  "schedule_id": "int | null - Schedule ID if selected via schedule",
  "expires_in_days": "int | null - Days until subscription expires",
  "is_active": "bool - Whether video is marked as active",
  "rotation_type": "string - Rotation type (none, sequential, cyclic)",
  "subscription_end": "datetime | null - Subscription end date",
  "selected_at": "datetime - Timestamp when video was selected",
  "video_created_at": "datetime | null - Video creation timestamp"
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/viewer/1/active-video"
```

**Note**: For sequential/cyclic rotation modes, the rotation state is automatically incremented after each request, ensuring the next video is selected on subsequent calls.

### Get Viewer Active Video by Unique ID
- **Method**: `GET`
- **URL**: `/api/viewer/ar/{unique_id}/active-video`
- **Description**: Get the active video for AR content viewer by unique ID. Same functionality as above, but uses unique_id instead of numeric ID.
- **Auth Required**: No

#### Path Parameters
```
unique_id: string (required) - Unique identifier for AR content
```

#### Response (Success)
```json
{
  "id": "int - Video ID",
  "title": "string - Video title",
  "video_url": "string - Video URL",
  "preview_url": "string - Preview URL",
  "thumbnail_url": "string - Thumbnail URL",
  "duration": "int - Video duration in seconds",
  "width": "int - Video width in pixels",
  "height": "int - Video height in pixels",
  "mime_type": "string - Video MIME type",
  "selection_source": "string - Selection source (schedule, active_default, rotation, fallback)",
  "schedule_id": "int | null - Schedule ID if selected via schedule",
  "expires_in_days": "int | null - Days until subscription expires",
  "is_active": "bool - Whether video is marked as active",
  "rotation_type": "string - Rotation type (none, sequential, cyclic)",
  "subscription_end": "datetime | null - Subscription end date",
  "selected_at": "datetime - Timestamp when video was selected",
  "video_created_at": "datetime | null - Video creation timestamp"
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/viewer/ar/unique-id/active-video"
```

---

## Settings

### Get Settings
- **Method**: `GET`
- **URL**: `/api/settings`
- **Description**: Get system settings
- **Auth Required**: Yes

#### Response (Success)
```json
{
  "project_name": "string - Project name",
  "version": "string - Version",
  "public_url": "string - Public URL",
  "media_root": "string - Media root path",
  "max_file_size_photo": "int - Max photo file size in bytes",
  "max_file_size_video": "int - Max video file size in bytes",
  "allowed_extensions_photo": "array - Allowed photo extensions",
  "allowed_extensions_video": "array - Allowed video extensions"
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/settings" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Health

### Health Status
- **Method**: `GET`
- **URL**: `/api/health/status`
- **Description**: Get application health status
- **Auth Required**: No

#### Response (Success)
```json
{
  "status": "string - Health status (healthy, degraded, unavailable)",
  "timestamp": "datetime - Check timestamp",
  "version": "string - Application version",
  "database": {
    "status": "string - Database connectivity status",
    "ping": "float - Database ping time in ms"
  },
  "disk_space": {
    "status": "string - Disk space status",
    "available": "string - Available disk space",
    "used": "string - Used disk space"
  }
}
```

#### Examples
```curl
curl -X GET "http://localhost:8000/api/health/status"
```

### Prometheus Metrics
- **Method**: `GET`
- **URL**: `/api/health/metrics`
- **Description**: Get Prometheus metrics endpoint
- **Auth Required**: No

#### Response
- 200: Plain text Prometheus metrics

#### Examples
```curl
curl -X GET "http://localhost:8000/api/health/metrics"
```

---

## WebSocket

### Alerts WebSocket
- **Method**: `WebSocket`
- **URL**: `/api/ws/alerts`
- **Description**: WebSocket endpoint for real-time alerts
- **Auth Required**: Yes

#### Connection Headers
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

#### Messages Sent by Server
```json
{
  "type": "alert",
  "level": "string - Alert level (info, warning, error)",
  "message": "string - Alert message",
  "timestamp": "datetime - Alert timestamp"
}
```

#### Examples
```javascript
const ws = new WebSocket('ws://localhost:8000/api/ws/alerts', {
  headers: {
    'Authorization': 'Bearer YOUR_ACCESS_TOKEN'
  }
});

ws.onopen = () => console.log('Connected to alerts');
ws.onmessage = (event) => console.log('Alert:', event.data);
ws.onclose = () => console.log('Disconnected from alerts');
```
