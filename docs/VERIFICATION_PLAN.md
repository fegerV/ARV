# Storage Providers Verification Plan

## Overview

This document enumerates the validation procedures for storage providers, including unit tests, integration tests, end-to-end tests, Celery task verification, and manual storage checks.

## Test Categories

### 1. Unit Tests
**Location:** `tests/unit/test_storage_providers.py`

**Test Coverage:**
- Storage provider factory methods
- Individual provider functionality
- Configuration validation
- Error handling scenarios

**Running Unit Tests:**
```bash
# Run all unit tests
pytest tests/unit/ -v --cov=app.services.storage

# Run storage-specific unit tests
pytest tests/unit/test_storage_providers.py -v

# Run with coverage report
pytest tests/unit/test_storage_providers.py -v --cov=app.services.storage --cov-report=html
```

**Expected Output:**
```
============================= test session starts ==============================
collected 15 items

tests/unit/test_storage_providers.py ...............               [100%]

============================== 15 passed in 2.34s ===============================
Coverage: app.services.storage 95%
```

### 2. Integration Tests
**Location:** `tests/integration/test_storage_integration.py`

**Test Categories:**
- API Endpoint Tests (CRUD operations, error handling)
- Database Integration (persistence, relationships)
- Provider Integration (real connections, file operations)

**Running Integration Tests:**
```bash
# Setup test environment
export DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/test_vertex_ar
export REDIS_URL=redis://localhost:6379/1
export STORAGE_TYPE=local
export STORAGE_BASE_PATH=/tmp/test_storage

# Start test services
docker compose -f docker-compose.test.yml up -d

# Run integration tests
pytest tests/integration/test_storage_integration.py -v
```

**Expected Output:**
```
============================= test session starts ==============================
collected 8 items

tests/integration/test_storage_integration.py ........               [100%]

============================== 8 passed in 15.67s ==============================
```

### 3. End-to-End Tests
**Location:** `tests/e2e/storage.spec.ts`

**Test Categories:**
- Admin Panel Storage Management
- File Upload Workflows
- Cross-Provider Operations

**Running E2E Tests:**
```bash
# Install Playwright dependencies
cd frontend && npm install && npx playwright install

# Run E2E tests
npx playwright test tests/e2e/storage.spec.ts

# Run with specific browser
npx playwright test tests/e2e/storage.spec.ts --project=chromium

# Run in headed mode for debugging
npx playwright test tests/e2e/storage.spec.ts --headed
```

**Expected Output:**
```
Running 3 tests using 3 workers
  ✓ Admin Panel Storage Management (45.2s)
  ✓ File Upload Workflows (32.1s)
  ✓ Cross-Provider Operations (28.7s)

  3 passed (106.0s)
```

### 4. Celery Task Verification

**Task Categories:**
- Thumbnail Generation Tasks
- File Processing Tasks
- Cleanup Tasks

**Running Celery Task Tests:**
```bash
# Start Celery worker
celery -A app.tasks.celery_app worker --loglevel=info

# Test thumbnail generation
python -c "
from app.tasks.thumbnail_generator import generate_video_thumbnail
result = generate_video_thumbnail.delay('test_video.mp4', 'test_output.jpg')
print(f'Task ID: {result.id}')
print(f'Status: {result.status}')
"

# Monitor task execution
celery -A app.tasks.celery_app events
```

**Expected Task Output:**
```
[2024-12-07 10:00:00,000: INFO/MainProcess] Task generate_video_thumbnail[abc123] received
[2024-12-07 10:00:05,000: INFO/MainProcess] Task generate_video_thumbnail[abc123] succeeded in 5.2s
```

## Manual Storage Checks

### Local Storage Verification
```bash
# Verify storage directory exists
ls -la /app/storage/content

# Check file permissions
stat /app/storage/content

# Test file creation
touch /app/storage/content/test_file.txt
echo "test content" > /app/storage/content/test_file.txt

# Verify file contents
cat /app/storage/content/test_file.txt

# Cleanup
rm /app/storage/content/test_file.txt
```

### MinIO Storage Verification
```bash
# Install MinIO client
curl https://dl.min.io/client/mc/release/linux-amd64/mc --create-dirs -o $HOME/minio-binaries/mc
chmod +x $HOME/minio-binaries/mc
export PATH=$PATH:$HOME/minio-binaries

# Configure MinIO client
mc alias set minio http://localhost:9000 ACCESS_KEY SECRET_KEY

# Test connection
mc admin info minio

# List buckets
mc ls minio

# Test file operations
mc cp /tmp/test.txt minio/vertex-ar/test.txt
mc ls minio/vertex-ar/
mc cat minio/vertex-ar/test.txt

# Cleanup
mc rm minio/vertex-ar/test.txt
```

### Yandex Disk Verification
```bash
# Test OAuth token
curl -H "Authorization: OAuth $YANDEX_DISK_OAUTH_TOKEN" https://cloud-api.yandex.net/v1/disk/

# List files
curl -H "Authorization: OAuth $YANDEX_DISK_OAUTH_TOKEN" https://cloud-api.yandex.net/v1/disk/resources?path=/VertexAR

# Upload test file
curl -X PUT \
  -H "Authorization: OAuth $YANDEX_DISK_OAUTH_TOKEN" \
  -H "Content-Type: text/plain" \
  -d "test content" \
  "https://cloud-api.yandex.net/v1/disk/resources/upload?path=/VertexAR/test.txt&overwrite=true"

# Cleanup
curl -X DELETE \
  -H "Authorization: OAuth $YANDEX_DISK_OAUTH_TOKEN" \
  https://cloud-api.yandex.net/v1/disk/resources?path=/VertexAR/test.txt
```

## Performance Benchmarks

### Expected Performance

| Provider | 1MB File | 10MB File | 100MB File |
|----------|----------|-----------|------------|
| Local Disk | < 0.01s | < 0.1s | < 1s |
| MinIO | 0.1-0.5s | 1-5s | 10-30s |
| Yandex Disk | 1-3s | 10-30s | 60-180s |

## Security Verification

### Access Control Tests
```bash
# Test unauthorized access
curl -i http://localhost:8000/api/storage/connections
# Expected: 401 Unauthorized

# Test with valid token
curl -i -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/storage/connections
# Expected: 200 OK

# Test injection attempts
curl -X POST -H "Content-Type: application/json" \
  -d '{"provider": "local_disk", "base_path": "../../../etc"}' \
  http://localhost:8000/api/storage/connections
# Expected: 400 Bad Request
```

## Success Criteria

### Automated Tests
- [ ] All unit tests pass (100% success rate)
- [ ] All integration tests pass (100% success rate)
- [ ] All E2E tests pass (100% success rate)
- [ ] Celery tasks execute without errors
- [ ] Code coverage > 90% for storage modules

### Manual Verification
- [ ] File upload/download works for all providers
- [ ] Presigned URLs generate and function correctly
- [ ] Connection tests pass for all configured providers
- [ ] Performance benchmarks meet requirements
- [ ] Security controls prevent unauthorized access

### Documentation
- [ ] Configuration examples are accurate
- [ ] API documentation is current
- [ ] Troubleshooting guide covers common issues
- [ ] Migration procedures are tested

## Failure Handling

### Common Failure Scenarios

1. **Test Environment Issues**
   - Database connection failures
   - Redis connectivity problems
   - Missing test data

2. **Provider-Specific Issues**
   - MinIO credentials invalid
   - Yandex Disk token expired
   - Local storage permissions

3. **Network Issues**
   - Firewall blocking connections
   - DNS resolution failures
   - SSL certificate problems

### Troubleshooting Steps

1. **Check Logs**
   ```bash
   # Application logs
   docker compose logs app
   
   # Celery logs
   docker compose logs celery
   
   # Database logs
   docker compose logs postgres
   ```

2. **Verify Configuration**
   ```bash
   # Check environment variables
   env | grep STORAGE
   
   # Test database connection
   docker compose exec postgres psql -U vertex_ar -c "SELECT 1"
   
   # Test Redis connection
   docker compose exec redis redis-cli ping
   ```

3. **Validate Network**
   ```bash
   # Test MinIO connectivity
   telnet minio-host 9000
   
   # Test Yandex Disk API
   curl -H "Authorization: OAuth $TOKEN" https://cloud-api.yandex.net/v1/disk/
   ```

## Automated Verification Script

The verification script (`scripts/run_verification.sh`) executes all tests sequentially:

```bash
#!/bin/bash
set -euo pipefail

echo "🔍 Starting Storage Providers Verification..."

# 1. Unit Tests
echo "📋 Running Unit Tests..."
pytest tests/unit/test_storage_providers.py -v --cov=app.services.storage

# 2. Integration Tests
echo "🔗 Running Integration Tests..."
pytest tests/integration/test_storage_integration.py -v

# 3. E2E Tests
echo "🌐 Running E2E Tests..."
cd frontend && npx playwright test tests/e2e/storage.spec.ts

# 4. Celery Task Tests
echo "⚙️ Testing Celery Tasks..."
python scripts/test_celery_tasks.py

# 5. Manual Storage Checks
echo "✅ Running Manual Storage Checks..."
python scripts/verify_storage_providers.py

echo "✨ All verification tests completed successfully!"
```

## Contact and Support

For verification issues or questions:
- **Development Team:** dev-team@vertexar.com
- **Documentation:** docs@vertexar.com
- **Emergency Support:** emergency@vertexar.com

---

*Last updated: December 2024*