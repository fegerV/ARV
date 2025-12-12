# Yandex OAuth Implementation

This document describes the enhanced Yandex OAuth implementation for the Vertex AR platform, providing secure authentication and storage integration with Yandex Disk.

## Overview

The OAuth implementation includes:
- Secure state management with Redis fallback to in-memory storage
- Token encryption for secure credential storage
- Enhanced error handling and logging
- Comprehensive API endpoints for folder management
- Safe connection listing without exposing secrets

## Architecture

### Components

1. **OAuthStateStore** (`app/utils/oauth_state.py`)
   - Manages OAuth state tokens with 5-minute TTL
   - Redis primary storage with in-memory fallback
   - Automatic cleanup of expired states

2. **TokenEncryption** (`app/utils/token_encryption.py`)
   - Encrypts OAuth tokens using Fernet symmetric encryption
   - Key derivation from SECRET_KEY using PBKDF2
   - Fallback to base64 encoding for development

3. **OAuth Routes** (`app/api/routes/oauth.py`)
   - `/api/oauth/yandex/authorize` - Initiates OAuth flow
   - `/api/oauth/yandex/callback` - Handles OAuth callback
   - `/api/oauth/yandex/{connection_id}/folders` - Lists folders
   - `/api/oauth/yandex/{connection_id}/create-folder` - Creates folders

4. **Storage Routes** (`app/api/routes/storage.py`)
   - `/api/storage/connections` - Lists connections safely

## Configuration

### Environment Variables

```bash
# Yandex Disk OAuth Configuration
YANDEX_OAUTH_CLIENT_ID=your-yandex-client-id
YANDEX_OAUTH_CLIENT_SECRET=your-yandex-client-secret
YANDEX_OAUTH_REDIRECT_URI=http://localhost:3000/storage/oauth/callback

# Required for token encryption
SECRET_KEY=your-secure-secret-key-min-32-chars

# Redis for state management (recommended)
REDIS_URL=redis://localhost:6379/0
```

### Yandex OAuth App Setup

1. Visit [Yandex OAuth](https://oauth.yandex.ru/client/new)
2. Create a new application with the following settings:
   - **Platform**: Web services
   - **Redirect URI**: `http://localhost:3000/storage/oauth/callback` (or your frontend URL)
   - **Permissions**: Yandex Disk API
   - **Scope**: `cloud_api:disk.read cloud_api:disk.write`

## API Endpoints

### 1. Initiate OAuth Flow

```http
GET /api/oauth/yandex/authorize?connection_name=My%20Yandex%20Disk
```

**Response**: Redirect to Yandex OAuth authorization page

**Features**:
- CSRF protection via state parameter
- Validates redirect URI configuration
- Secure logging without exposing secrets

### 2. OAuth Callback

```http
GET /api/oauth/yandex/callback?code=auth_code&state=state_token
```

**Response**: Redirect to frontend with success parameter

**Features**:
- State validation and consumption
- Token exchange with error handling
- Disk metadata retrieval
- Encrypted credential storage
- Comprehensive error mapping

### 3. List Folders

```http
GET /api/oauth/yandex/{connection_id}/folders?path=/folder
```

**Response**:
```json
{
  "current_path": "/folder",
  "folders": [
    {
      "name": "Documents",
      "path": "/folder/Documents",
      "type": "dir",
      "created": "2023-01-01T10:00:00Z",
      "modified": "2023-12-01T15:30:00Z",
      "last_modified": "2023-12-01T15:30:00Z"
    }
  ],
  "parent_path": "/",
  "has_parent": true
}
```

**Features**:
- Token decryption on demand
- Directory filtering (only `type == "dir"`)
- Last-modified timestamps
- Parent path navigation
- Yandex API error mapping (401/403/404/timeout)

### 4. Create Folder

```http
POST /api/oauth/yandex/{connection_id}/create-folder?folder_path=/NewFolder
```

**Response**:
```json
{
  "status": "success",
  "message": "Folder created: /NewFolder",
  "path": "/NewFolder"
}
```

**Features**:
- Token decryption
- Specific error handling (409 for existing folders)
- Network timeout handling

### 5. List Storage Connections

```http
GET /api/storage/connections?provider=yandex_disk&is_active=true
```

**Response**:
```json
{
  "connections": [
    {
      "id": 1,
      "name": "My Yandex Disk",
      "provider": "yandex_disk",
      "is_active": true,
      "is_default": false,
      "test_status": "success",
      "last_tested_at": "2023-12-01T15:30:00Z",
      "created_at": "2023-12-01T10:00:00Z",
      "updated_at": "2023-12-01T15:30:00Z",
      "user_display_name": "John Doe",
      "total_space": 10737418240,
      "used_space": 5368709120,
      "has_encryption": true
    }
  ],
  "total": 1,
  "filters": {
    "provider": "yandex_disk",
    "is_active": true
  }
}
```

**Features**:
- Safe metadata without exposing credentials
- Provider and status filtering
- Yandex-specific metadata (user info, storage usage)
- Encryption status indicator

## Security Features

### 1. State Management
- **CSRF Protection**: Unique state tokens for each OAuth attempt
- **TTL**: 5-minute expiration for state tokens
- **One-time Use**: States are consumed after validation
- **Redis Fallback**: In-memory storage if Redis unavailable

### 2. Token Encryption
- **Fernet Encryption**: Symmetric encryption with authenticated cryptography
- **Key Derivation**: PBKDF2 with 100,000 iterations
- **Secure Storage**: Encrypted tokens in database
- **Development Fallback**: Base64 encoding for non-production

### 3. Error Handling
- **No Secret Leakage**: Sanitized logging and error messages
- **Specific Error Codes**: Mapped HTTP status codes for different failure types
- **Network Resilience**: Timeout and connection error handling
- **Graceful Degradation**: Fallback mechanisms for component failures

## Error Handling

### OAuth Flow Errors

| Error Type | HTTP Status | User Message |
|-------------|-------------|--------------|
| Invalid state | 400 | Invalid or expired state parameter |
| Invalid code | 400 | Failed to exchange authorization code |
| Network error | 503 | Network error during authentication |
| Disk access denied | 400 | Failed to access Yandex Disk. Please check permissions |

### Folder Operations Errors

| Error Type | HTTP Status | User Message |
|-------------|-------------|--------------|
| Token expired | 401 | OAuth token expired or invalid. Please re-authenticate |
| Access denied | 403 | Access denied to this folder. Please check permissions |
| Folder not found | 404 | Folder not found in Yandex Disk |
| Folder exists | 409 | Folder already exists at this location |
| Network timeout | 504 | Request to Yandex Disk timed out. Please try again |

## Testing

### Unit Tests
- OAuth state management (Redis and in-memory)
- Token encryption/decryption
- Error handling scenarios

### Integration Tests
- Complete OAuth flow
- Folder operations
- Error mapping
- Connection listing

### Running Tests

```bash
# Run unit tests
pytest tests/unit/test_oauth_state.py
pytest tests/unit/test_token_encryption.py

# Run integration tests
pytest tests/integration/test_oauth_flow.py

# Run all OAuth tests
pytest tests/unit/test_oauth*.py tests/integration/test_oauth*.py -v
```

## Frontend Integration

### OAuth Flow
1. **Initiate**: Call `/api/oauth/yandex/authorize` with connection name
2. **Popup**: Open the returned URL in a popup window
3. **Callback**: Handle the redirect back to your frontend
4. **Success**: Extract connection ID from URL parameters

### Folder Browser
1. **List**: Call `/api/oauth/yandex/{connection_id}/folders`
2. **Navigate**: Use `parent_path` and current path for navigation
3. **Create**: Call `/api/oauth/yandex/{connection_id}/create-folder`

### Connection Management
1. **List**: Call `/api/storage/connections` with filters
2. **Display**: Show metadata without exposing secrets
3. **Status**: Use `test_status` and `last_tested_at` for connection health

## Monitoring and Logging

### Structured Logging
All OAuth operations include structured logging with:
- **Connection ID**: For tracking specific connections
- **Operation Type**: Authorize, callback, folder operations
- **Error Context**: Sanitized error information
- **Performance Metrics**: Request timing and success rates

### Key Metrics
- OAuth success/failure rates
- Token expiration frequency
- Folder operation performance
- State store usage patterns

## Troubleshooting

### Common Issues

1. **Invalid redirect URI**
   - Check Yandex OAuth app configuration
   - Verify `YANDEX_OAUTH_REDIRECT_URI` environment variable

2. **State token expired**
   - OAuth flow took longer than 5 minutes
   - User may need to restart the authorization process

3. **Token decryption failures**
   - Check `SECRET_KEY` consistency
   - Verify encryption key derivation

4. **Redis connection issues**
   - System falls back to in-memory storage
   - Check Redis connectivity and configuration

### Debug Mode
Enable debug logging by setting:
```bash
LOG_LEVEL=DEBUG
DEBUG=true
```

This provides detailed error information without exposing secrets.

## Migration Notes

### From Previous Implementation
- **State Storage**: Migrated from in-memory to Redis with fallback
- **Token Storage**: Added encryption for existing connections
- **Error Handling**: Enhanced with specific error codes and messages
- **API Responses**: Standardized response formats

### Backward Compatibility
- Legacy encrypted tokens are supported
- Existing connections continue to work
- API endpoints maintain backward compatibility

## Security Considerations

### Production Deployment
1. **Use Redis**: Enable Redis for state management
2. **Secure SECRET_KEY**: Use a strong, unique secret key
3. **HTTPS**: Ensure all OAuth callbacks use HTTPS
4. **Environment Variables**: Store secrets in environment variables

### Token Security
- Tokens are encrypted at rest
- Access tokens have limited lifetime
- Refresh tokens are stored securely
- Automatic token refresh can be implemented

## Future Enhancements

### Planned Features
1. **Automatic Token Refresh**: Handle token expiration automatically
2. **Multiple Providers**: Extend to other storage providers
3. **Enhanced Monitoring**: Add Prometheus metrics
4. **Rate Limiting**: Implement OAuth flow rate limiting
5. **Webhook Support**: Yandex Disk change notifications

### Scalability
- Distributed state management with Redis Cluster
- Connection pooling for Yandex API requests
- Caching for folder metadata
- Async processing for large file operations

## Support

For issues or questions about the OAuth implementation:
1. Check the application logs for detailed error information
2. Verify environment variable configuration
3. Ensure Yandex OAuth app settings match redirect URI
4. Test Redis connectivity if using distributed state management