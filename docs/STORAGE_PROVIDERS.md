# Storage Providers Guide

## Overview

The Vertex AR B2B Platform supports multiple storage providers through a unified interface. This guide explains each provider, required configuration, factory behavior, and usage examples.

## Supported Providers

### 1. Local Disk Storage

**Provider ID:** `local_disk`

**Description:** Filesystem-based storage for development and small deployments.

#### Required Configuration

| Parameter | Type | Required | Example |
|-----------|------|----------|---------|
| `base_path` | string | Yes | `/app/storage/content` |

#### Environment Variables

```env
STORAGE_TYPE=local
STORAGE_BASE_PATH=/app/storage/content
```

#### API Payload Example

```json
{
  "name": "Local Development Storage",
  "provider": "local_disk",
  "base_path": "/app/storage/content",
  "is_default": true,
  "credentials": {}
}
```

#### Use Cases
- Development environments
- Small production deployments (< 100GB)
- When external storage is not required

#### Limitations
- No built-in redundancy
- Limited to single server
- Manual backup required

### 2. MinIO Object Storage

**Provider ID:** `minio`

**Description:** S3-compatible object storage for scalable production deployments.

#### Required Configuration

| Parameter | Type | Required | Example |
|-----------|------|----------|---------|
| `endpoint` | string | Yes | `minio.example.com:9000` |
| `access_key` | string | Yes | `AKIAIOSFODNN7EXAMPLE` |
| `secret_key` | string | Yes | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `bucket_name` | string | Yes | `vertex-ar` |
| `secure` | boolean | No | `true` |
| `region` | string | No | `us-east-1` |

#### Environment Variables

```env
STORAGE_TYPE=minio
MINIO_ENDPOINT=minio.example.com:9000
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
MINIO_BUCKET_NAME=vertex-ar
MINIO_REGION=us-east-1
MINIO_SECURE=true
```

#### API Payload Example

```json
{
  "name": "Production MinIO Storage",
  "provider": "minio",
  "base_path": "/vertex-ar",
  "is_default": true,
  "credentials": {
    "endpoint": "minio.example.com:9000",
    "access_key": "AKIAIOSFODNN7EXAMPLE",
    "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "secure": true,
    "region": "us-west-2",
    "bucket_name": "vertex-ar-production"
  }
}
```

#### Use Cases
- Production environments
- Large-scale deployments (> 100GB)
- Multi-server setups
- When S3 compatibility is required

#### Features
- Presigned URLs for direct uploads
- Automatic multipart uploads
- Built-in redundancy
- S3 API compatibility

### 3. Yandex Disk Storage

**Provider ID:** `yandex_disk`

**Description:** Cloud storage integration with Yandex's personal cloud service.

#### Required Configuration

| Parameter | Type | Required | Example |
|-----------|------|----------|---------|
| `oauth_token` | string | Yes | `AQAAAAAEXAMPLE_TOKEN` |
| `base_path` | string | No | `/VertexAR` |
| `refresh_token` | string | No | `REFRESH_TOKEN_OPTIONAL` |
| `expires_at` | datetime | No | `2024-12-31T23:59:59Z` |

#### Environment Variables

```env
STORAGE_TYPE=yandex_disk
YANDEX_DISK_OAUTH_TOKEN=your-yandex-oauth-token
YANDEX_DISK_BASE_PATH=/VertexAR
```

#### API Payload Example

```json
{
  "name": "Yandex Disk Production",
  "provider": "yandex_disk",
  "base_path": "/VertexAR/Production",
  "is_default": true,
  "credentials": {
    "oauth_token": "AQAAAAAEXAMPLE_TOKEN",
    "refresh_token": "REFRESH_TOKEN_OPTIONAL",
    "expires_at": "2024-12-31T23:59:59Z"
  }
}
```

#### Use Cases
- Russian market deployments
- When Yandex ecosystem integration is desired
- Small to medium production deployments

#### Features
- OAuth authentication
- Automatic token refresh
- Cloud-based redundancy
- Yandex ecosystem integration

---

## Storage Provider Factory

The `StorageProviderFactory` creates and configures storage providers based on the provider type and configuration.

### Factory Pattern

```python
from app.services.storage.factory import StorageProviderFactory

# Create provider
provider = StorageProviderFactory.create_provider(
    provider_type="minio",
    config={
        "endpoint": "minio:9000",
        "access_key": "key",
        "secret_key": "secret",
        "bucket_name": "vertex-ar"
    }
)
```

### Provider Interface

All providers implement the `BaseStorageProvider` interface:

```python
class BaseStorageProvider:
    async def upload_file(self, local_path: str, remote_path: str) -> str
    async def download_file(self, remote_path: str, local_path: str) -> None
    async def delete_file(self, remote_path: str) -> None
    async def list_files(self, prefix: str = "") -> List[str]
    async def generate_presigned_url(
        self, 
        remote_path: str, 
        expires_in: int = 3600,
        method: str = "PUT"
    ) -> str
    async def test_connection(self) -> bool
```

---

## Configuration Examples

### Development Environment (.env)

```env
# Use local storage for development
STORAGE_TYPE=local
STORAGE_BASE_PATH=./storage/content
```

### Staging Environment (.env)

```env
# Use MinIO for staging
STORAGE_TYPE=minio
MINIO_ENDPOINT=staging-minio:9000
MINIO_ACCESS_KEY=staging-key
MINIO_SECRET_KEY=staging-secret
MINIO_BUCKET_NAME=vertex-ar-staging
MINIO_REGION=us-east-1
MINIO_SECURE=false
```

### Production Environment (.env)

```env
# Use Yandex Disk for production
STORAGE_TYPE=yandex_disk
YANDEX_DISK_OAUTH_TOKEN=AQAAAAAEXAMPLE_PRODUCTION_TOKEN
YANDEX_DISK_BASE_PATH=/VertexAR/Production
```

---

## Migration Guide

### From Local to MinIO

1. **Update Configuration:**
   ```env
   STORAGE_TYPE=minio
   MINIO_ENDPOINT=minio:9000
   MINIO_ACCESS_KEY=new-key
   MINIO_SECRET_KEY=new-secret
   MINIO_BUCKET_NAME=vertex-ar
   ```

2. **Data Migration:**
   ```bash
   # Use rclone or similar tool
   rclone copy /app/storage/content minio:vertex-ar/
   ```

3. **Verify Connection:**
   ```python
   from app.core.storage import get_storage_provider
   provider = get_storage_provider()
   await provider.test_connection()
   ```

### From MinIO to Yandex Disk

1. **Export Data from MinIO:**
   ```bash
   rclone copy minio:vertex-ar/ ./backup/
   ```

2. **Update Configuration:**
   ```env
   STORAGE_TYPE=yandex_disk
   YANDEX_DISK_OAUTH_TOKEN=new-token
   YANDEX_DISK_BASE_PATH=/VertexAR
   ```

3. **Import to Yandex Disk:**
   ```bash
   rclone copy ./backup/ yandex:/VertexAR/
   ```

---

## Security Considerations

### Access Credentials

- **MinIO:** Use IAM policies and rotate keys regularly
- **Yandex Disk:** Use OAuth with minimal scopes
- **Local Storage:** Set appropriate filesystem permissions

### Network Security

- **MinIO:** Enable TLS in production (`MINIO_SECURE=true`)
- **Yandex Disk:** All traffic encrypted by default
- **Local Storage:** Use VPN for remote access

### Data Encryption

- **MinIO:** Supports server-side and client-side encryption
- **Yandex Disk:** Encrypted at rest and in transit
- **Local Storage:** Use filesystem encryption (LUKS, BitLocker)

---

## Monitoring and Troubleshooting

### Health Checks

```bash
# Test storage provider
curl -X GET http://localhost:8000/api/storage/connections

# Test specific connection
curl -X POST http://localhost:8000/api/storage/connections/{id}/test
```

### Common Issues

1. **MinIO Connection Failed:**
   - Check endpoint accessibility
   - Verify credentials
   - Ensure bucket exists

2. **Yandex Disk Token Expired:**
   - Refresh OAuth token
   - Check token permissions
   - Re-authenticate if needed

3. **Local Storage Permissions:**
   - Check directory permissions
   - Verify disk space
   - Validate path existence

### Logging

Storage operations are logged with structured logging:

```json
{
  "event": "file_uploaded",
  "provider": "minio",
  "remote_path": "/content/video.mp4",
  "size_bytes": 1048576,
  "duration_ms": 245
}
```

---

## Performance Considerations

### Throughput

| Provider | Upload Speed | Download Speed | Concurrent Connections |
|----------|--------------|----------------|-----------------------|
| Local Disk | 500+ MB/s | 500+ MB/s | Unlimited |
| MinIO | 100+ MB/s | 100+ MB/s | 1000+ |
| Yandex Disk | 10-50 MB/s | 10-50 MB/s | 10-20 |

### Latency

| Provider | Average Latency | 95th Percentile |
|----------|----------------|-----------------|
| Local Disk | < 1ms | < 2ms |
| MinIO | 10-50ms | 100ms |
| Yandex Disk | 100-500ms | 1s |

---

## Best Practices

### Configuration Management

1. **Use environment variables** for all credentials
2. **Never commit secrets** to version control
3. **Rotate credentials regularly** (every 90 days)
4. **Use different credentials** per environment

### Data Organization

1. **Use consistent naming** conventions
2. **Organize by company/project** structure
3. **Implement retention policies** for old data
4. **Monitor storage usage** and set alerts

### Backup Strategy

1. **Automate daily backups** for production
2. **Test restore procedures** regularly
3. **Store backups in different regions**
4. **Document recovery procedures**

---

## API Reference

### Storage Connections API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/storage/connections` | List all storage connections |
| POST | `/api/storage/connections` | Create new storage connection |
| GET | `/api/storage/connections/{id}` | Get specific connection |
| PUT | `/api/storage/connections/{id}` | Update connection |
| DELETE | `/api/storage/connections/{id}` | Delete connection |
| POST | `/api/storage/minio/presign-upload` | Generate MinIO presigned URL |

### Connection Testing

```bash
# Test MinIO connection
curl -X POST http://localhost:8000/api/storage/connections/1/test \
  -H "Authorization: Bearer $TOKEN"
```

---

## Troubleshooting Checklist

### Before Deployment

- [ ] Storage provider credentials configured
- [ ] Network connectivity tested
- [ ] Permissions verified
- [ ] Backup strategy documented
- [ ] Monitoring configured

### After Deployment

- [ ] Connection tests passing
- [ ] File upload/download working
- [ ] Presigned URLs functional
- [ ] Error logging enabled
- [ ] Performance baseline established

---

## Support and Resources

- **Documentation:** [Vertex AR Docs](../README.md)
- **API Reference:** [API Documentation](../API_DOCUMENTATION.md)
- **Troubleshooting:** Check application logs
- **Community:** Contact development team

---

*Last updated: December 2024*