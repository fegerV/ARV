# MinIO Presigned URLs Implementation

## Overview

This document describes the implementation of presigned URLs for direct browser uploads to MinIO, bypassing the backend server for improved performance and reduced load.

## Architecture

The implementation follows a three-tier approach:

1. **Frontend** - Requests presigned URL from backend
2. **Backend** - Generates presigned URL using MinIO SDK
3. **MinIO** - Accepts direct upload from browser

```
Browser → Backend API → MinIO (generate presigned URL)
Browser → MinIO (direct upload using presigned URL)
```

## Backend Implementation

### Storage Provider Factory

The system uses a factory pattern to create storage provider instances:

```
app/
├── services/
│   └── storage/
│       ├── factory.py              # Provider factory
│       └── providers/
│           ├── base.py             # Abstract base class
│           ├── minio_provider.py   # MinIO implementation
│           ├── local_disk_provider.py
│           └── yandex_disk_provider.py
└── api/
    └── routes/
        └── storage.py             # API endpoints
```

### MinIO Provider Features

The `MinIOProvider` class implements the `StorageProvider` interface with specific support for presigned URLs:

```python
async def generate_presigned_url(self, remote_path: str, expires_in: int = 3600, method: str = "PUT") -> str:
    """
    Generate a presigned URL for direct browser upload/download.
    
    Args:
        remote_path: Path to the file in MinIO
        expires_in: Number of seconds until the URL expires (default: 1 hour)
        method: HTTP method for the presigned URL (GET, PUT, POST)
        
    Returns:
        Presigned URL for direct access to the file
    """
    url = self.client.presigned_url(
        method,
        self.bucket_name,
        remote_path,
        expires=timedelta(seconds=expires_in)
    )
    return url
```

### API Endpoint

The `/api/storage/minio/presign-upload` endpoint generates presigned URLs:

```python
@router.post("/storage/minio/presign-upload", response_model=PresignedURLResponse)
async def generate_minio_presigned_url(
    request: PresignedURLRequest,
    connection_id: int,
    db: AsyncSession = Depends(get_db)
):
    # Validate connection
    # Generate presigned URL
    # Return URL to frontend
```

## Frontend Implementation

### MinIO Service

The frontend service handles API communication and direct uploads:

```typescript
class MinIOService {
  async generatePresignedURL(connectionId: number, request: PresignedURLRequest): Promise<PresignedURLResponse> {
    // Call backend API to generate presigned URL
  }

  async uploadFileWithPresignedURL(presignedUrl: string, file: File, onProgress?: (progress: number) => void): Promise<void> {
    // Upload file directly to MinIO using XMLHttpRequest
  }
}
```

### React Component

The `MinioDirectUpload` component provides a UI for direct uploads:

```tsx
<MinioDirectUpload
  connectionId={123}
  bucket="my-bucket"
  onUploadComplete={(objectName) => console.log('Uploaded:', objectName)}
/>
```

## Security Considerations

### IAM Policy

The backend service account requires minimal permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AppWriteAccess",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:AbortMultipartUpload"
      ],
      "Resource": "arn:aws:s3:::bucket-name/*"
    }
  ]
}
```

### CORS Configuration

MinIO must allow cross-origin requests from the frontend:

```xml
<CORSConfiguration>
  <CORSRule>
    <AllowedOrigin>https://admin.vertexar.com</AllowedOrigin>
    <AllowedOrigin>http://localhost:3000</AllowedOrigin>
    <AllowedMethod>GET</AllowedMethod>
    <AllowedMethod>PUT</AllowedMethod>
    <AllowedMethod>POST</AllowedMethod>
    <AllowedMethod>DELETE</AllowedMethod>
    <AllowedHeader>*</AllowedHeader>
    <ExposeHeader>ETag</ExposeHeader>
    <ExposeHeader>x-amz-request-id</ExposeHeader>
    <MaxAgeSeconds>3000</MaxAgeSeconds>
  </CORSRule>
</CORSConfiguration>
```

Apply with:
```bash
mc cors set myminio/bucket-name cors.xml
```

## Benefits

1. **Reduced Backend Load** - Files uploaded directly to MinIO
2. **Improved Performance** - Eliminates backend bottleneck
3. **Better Scalability** - MinIO handles upload traffic
4. **Progress Tracking** - Real-time upload progress feedback
5. **Security** - Temporary, scoped access tokens

## Usage Flow

1. User selects file in frontend
2. Frontend requests presigned URL from backend
3. Backend validates request and generates presigned URL
4. Frontend receives URL and uploads directly to MinIO
5. Upload progress tracked in real-time
6. Completion callback triggered

## Error Handling

The system includes comprehensive error handling:

- Network errors during upload
- Expired presigned URLs
- Permission denied errors
- File size limits
- Invalid request parameters

## Testing

### Backend Tests

```python
def test_generate_presigned_url():
    # Test valid presigned URL generation
    # Test invalid connection ID
    # Test non-MinIO connections
    # Test error handling
```

### Frontend Tests

```typescript
describe('MinIO Service', () => {
  it('should generate presigned URL', async () => {
    // Test presigned URL generation
  });
  
  it('should upload file with presigned URL', async () => {
    // Test direct file upload
  });
});
```

## Deployment

### Environment Variables

```
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
MINIO_SECURE=false
```

### MinIO Configuration

1. Create service account with minimal permissions
2. Configure CORS for frontend domains
3. Set up bucket policies
4. Test connectivity

## Future Enhancements

1. **Multipart Uploads** - Support for large file uploads
2. **Resume Capability** - Upload resumption after interruption
3. **Chunked Uploads** - Parallel upload chunks
4. **Advanced Progress** - Detailed upload analytics
5. **Retry Logic** - Automatic retry on transient failures
6. **Compression** - Automatic file compression before upload

## Files Created

1. `app/services/storage/factory.py` - Storage provider factory
2. `app/services/storage/providers/base.py` - Abstract base class
3. `app/services/storage/providers/minio_provider.py` - MinIO provider with presigned URL support
4. `app/services/storage/providers/local_disk_provider.py` - Local disk provider
5. `app/services/storage/providers/yandex_disk_provider.py` - Yandex Disk provider (placeholder)
6. `app/api/routes/storage.py` - Updated with presigned URL endpoint
7. `frontend/src/services/minioService.ts` - Frontend service for MinIO operations
8. `frontend/src/components/MinioDirectUpload.tsx` - React component for direct uploads
9. `MINIO_PRESIGNED_URLS.md` - This documentation file

## Integration Points

The presigned URL system integrates with:

1. **Storage Connections Management** - Uses existing connection infrastructure
2. **Company Storage Settings** - Respects company-specific storage configurations
3. **Authentication System** - Validates user permissions before URL generation
4. **Logging System** - Tracks presigned URL generation and usage
5. **Error Handling** - Consistent error responses with existing system

This implementation provides a robust, scalable solution for direct browser uploads to MinIO while maintaining security and performance best practices.