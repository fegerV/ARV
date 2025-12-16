"""Integration tests for OAuth flow endpoints."""

import pytest
import json
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.storage import StorageConnection
from app.utils.oauth_state import oauth_state_store


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
async def mock_yandex_token_response():
    """Mock Yandex OAuth token response."""
    return {
        "access_token": "test_access_token_12345",
        "refresh_token": "test_refresh_token_67890",
        "expires_in": 3600,
        "token_type": "bearer"
    }


@pytest.fixture
async def mock_yandex_disk_info():
    """Mock Yandex Disk info response."""
    return {
        "user": {
            "display_name": "Test User",
            "login": "testuser"
        },
        "total_space": 10737418240,  # 10GB
        "used_space": 5368709120,   # 5GB
        "trash_size": 107374182      # 100MB
    }


class TestOAuthFlow:
    """Integration tests for OAuth flow."""

    @pytest.mark.asyncio
    async def test_authorize_endpoint_success(self, client):
        """Test OAuth authorization endpoint success."""
        with patch('app.utils.oauth_state.oauth_state_store') as mock_store:
            mock_store.create_state = AsyncMock(return_value="test_state_123")
            
            response = client.get(
                "/api/oauth/yandex/authorize",
                params={"connection_name": "test_connection"}
            )
            
            assert response.status_code == 307  # Redirect
            assert "oauth.yandex.ru" in response.headers["location"]
            assert "test_state_123" in response.headers["location"]
            mock_store.create_state.assert_called_once_with("test_connection")

    @pytest.mark.asyncio
    async def test_authorize_endpoint_no_redirect_uri(self, client):
        """Test OAuth authorization with no redirect URI configured."""
        with patch('app.core.config.settings.YANDEX_OAUTH_REDIRECT_URI', ""):
            response = client.get(
                "/api/oauth/yandex/authorize",
                params={"connection_name": "test_connection"}
            )
            
            assert response.status_code == 500
            assert "YANDEX_OAUTH_REDIRECT_URI not configured" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_callback_success(self, client, mock_db_session, mock_yandex_token_response, mock_yandex_disk_info):
        """Test OAuth callback success."""
        # Mock state store
        with patch('app.utils.oauth_state.oauth_state_store') as mock_store:
            mock_store.get_and_delete_state = AsyncMock(return_value={
                "connection_name": "test_connection",
                "timestamp": 1234567890,
                "metadata": {}
            })
            mock_store.cleanup_expired_states = AsyncMock(return_value=0)
            
            # Mock HTTP requests
            with patch('httpx.AsyncClient') as mock_client:
                # Mock token exchange
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_yandex_token_response
                
                # Mock disk info
                mock_disk_response = AsyncMock()
                mock_disk_response.status_code = 200
                mock_disk_response.json.return_value = mock_yandex_disk_info
                
                mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
                mock_client.return_value.__aenter__.return_value.get.return_value = mock_disk_response
                
                # Mock database operations
                with patch('app.api.routes.oauth.get_db') as mock_get_db:
                    mock_get_db.return_value = mock_db_session
                    
                    with patch('app.api.routes.oauth.token_encryption') as mock_encryption:
                        mock_encryption.encrypt_credentials.return_value = "encrypted_credentials"
                        mock_encryption.is_encryption_available.return_value = True
                        
                        response = client.get(
                            "/api/oauth/yandex/callback",
                            params={"code": "test_auth_code", "state": "test_state"}
                        )
                        
                        assert response.status_code == 307  # Redirect
                        assert "success=true" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_callback_invalid_state(self, client):
        """Test OAuth callback with invalid state."""
        with patch('app.utils.oauth_state.oauth_state_store') as mock_store:
            mock_store.get_and_delete_state = AsyncMock(return_value=None)
            
            response = client.get(
                "/api/oauth/yandex/callback",
                params={"code": "test_auth_code", "state": "invalid_state"}
            )
            
            assert response.status_code == 400
            assert "Invalid or expired state parameter" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_callback_token_exchange_failure(self, client, mock_db_session):
        """Test OAuth callback with token exchange failure."""
        with patch('app.utils.oauth_state.oauth_state_store') as mock_store:
            mock_store.get_and_delete_state = AsyncMock(return_value={
                "connection_name": "test_connection",
                "timestamp": 1234567890
            })
            
            with patch('httpx.AsyncClient') as mock_client:
                mock_response = AsyncMock()
                mock_response.status_code = 400
                mock_response.text = "Invalid grant"
                
                mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
                
                with patch('app.api.routes.oauth.get_db') as mock_get_db:
                    mock_get_db.return_value = mock_db_session
                    
                    response = client.get(
                        "/api/oauth/yandex/callback",
                        params={"code": "invalid_code", "state": "test_state"}
                    )
                    
                    assert response.status_code == 400
                    assert "Failed to exchange authorization code" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_callback_disk_info_failure(self, client, mock_db_session, mock_yandex_token_response):
        """Test OAuth callback with disk info failure."""
        with patch('app.utils.oauth_state.oauth_state_store') as mock_store:
            mock_store.get_and_delete_state = AsyncMock(return_value={
                "connection_name": "test_connection",
                "timestamp": 1234567890
            })
            
            with patch('httpx.AsyncClient') as mock_client:
                # Mock successful token exchange
                mock_token_response = AsyncMock()
                mock_token_response.status_code = 200
                mock_token_response.json.return_value = mock_yandex_token_response
                
                # Mock failed disk info
                mock_disk_response = AsyncMock()
                mock_disk_response.status_code = 403
                mock_disk_response.text = "Access denied"
                
                mock_client.return_value.__aenter__.return_value.post.return_value = mock_token_response
                mock_client.return_value.__aenter__.return_value.get.return_value = mock_disk_response
                
                with patch('app.api.routes.oauth.get_db') as mock_get_db:
                    mock_get_db.return_value = mock_db_session
                    
                    response = client.get(
                        "/api/oauth/yandex/callback",
                        params={"code": "test_auth_code", "state": "test_state"}
                    )
                    
                    assert response.status_code == 400
                    assert "Failed to access Yandex Disk" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_folders_success(self, client, mock_db_session, mock_yandex_disk_info):
        """Test listing folders successfully."""
        # Mock storage connection
        mock_connection = StorageConnection(
            id=1,
            name="test_connection",
            provider="yandex_disk",
            credentials="encrypted_credentials",
            is_active=True
        )
        
        with patch('app.api.routes.oauth.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db_session
            mock_db_session.get = AsyncMock(return_value=mock_connection)
            
            # Mock token decryption
            with patch('app.api.routes.oauth.token_encryption') as mock_encryption:
                mock_encryption.decrypt_credentials.return_value = {
                    "oauth_token": "test_access_token"
                }
                
                # Mock Yandex API response
                with patch('httpx.AsyncClient') as mock_client:
                    mock_response = AsyncMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "_embedded": {
                            "items": [
                                {
                                    "name": "Documents",
                                    "path": "/Documents",
                                    "type": "dir",
                                    "created": "2023-01-01T10:00:00Z",
                                    "modified": "2023-12-01T15:30:00Z"
                                },
                                {
                                    "name": "Photos",
                                    "path": "/Photos",
                                    "type": "dir",
                                    "created": "2023-02-01T10:00:00Z",
                                    "modified": "2023-11-15T12:00:00Z"
                                },
                                {
                                    "name": "file.txt",
                                    "path": "/file.txt",
                                    "type": "file",
                                    "created": "2023-03-01T10:00:00Z",
                                    "modified": "2023-10-01T10:00:00Z"
                                }
                            ]
                        }
                    }
                    
                    mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
                    
                    response = client.get(
                        "/api/oauth/yandex/1/folders",
                        params={"path": "/"}
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    
                    assert data["current_path"] == "/"
                    assert data["parent_path"] == "/"
                    assert data["has_parent"] is False
                    assert len(data["folders"]) == 2  # Only directories
                    
                    folder_names = [folder["name"] for folder in data["folders"]]
                    assert "Documents" in folder_names
                    assert "Photos" in folder_names
                    assert "file.txt" not in folder_names  # File should be filtered out

    @pytest.mark.asyncio
    async def test_list_folders_unauthorized(self, client, mock_db_session):
        """Test listing folders with unauthorized access."""
        mock_connection = StorageConnection(
            id=1,
            name="test_connection",
            provider="yandex_disk",
            credentials="encrypted_credentials",
            is_active=True
        )
        
        with patch('app.api.routes.oauth.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db_session
            mock_db_session.get = AsyncMock(return_value=mock_connection)
            
            with patch('app.api.routes.oauth.token_encryption') as mock_encryption:
                mock_encryption.decrypt_credentials.return_value = {
                    "oauth_token": "expired_token"
                }
                
                with patch('httpx.AsyncClient') as mock_client:
                    mock_response = AsyncMock()
                    mock_response.status_code = 401
                    
                    mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
                    
                    response = client.get(
                        "/api/oauth/yandex/1/folders",
                        params={"path": "/"}
                    )
                    
                    assert response.status_code == 401
                    assert "OAuth token expired or invalid" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_folder_success(self, client, mock_db_session):
        """Test creating a folder successfully."""
        mock_connection = StorageConnection(
            id=1,
            name="test_connection",
            provider="yandex_disk",
            credentials="encrypted_credentials",
            is_active=True
        )
        
        with patch('app.api.routes.oauth.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db_session
            mock_db_session.get = AsyncMock(return_value=mock_connection)
            
            with patch('app.api.routes.oauth.token_encryption') as mock_encryption:
                mock_encryption.decrypt_credentials.return_value = {
                    "oauth_token": "test_access_token"
                }
                
                with patch('httpx.AsyncClient') as mock_client:
                    mock_response = AsyncMock()
                    mock_response.status_code = 201  # Created
                    
                    mock_client.return_value.__aenter__.return_value.put.return_value = mock_response
                    
                    response = client.post(
                        "/api/oauth/yandex/1/create-folder",
                        params={"folder_path": "/NewFolder"}
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["status"] == "success"
                    assert "NewFolder" in data["message"]
                    assert data["path"] == "/NewFolder"

    @pytest.mark.asyncio
    async def test_create_folder_already_exists(self, client, mock_db_session):
        """Test creating a folder that already exists."""
        mock_connection = StorageConnection(
            id=1,
            name="test_connection",
            provider="yandex_disk",
            credentials="encrypted_credentials",
            is_active=True
        )
        
        with patch('app.api.routes.oauth.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db_session
            mock_db_session.get = AsyncMock(return_value=mock_connection)
            
            with patch('app.api.routes.oauth.token_encryption') as mock_encryption:
                mock_encryption.decrypt_credentials.return_value = {
                    "oauth_token": "test_access_token"
                }
                
                with patch('httpx.AsyncClient') as mock_client:
                    mock_response = AsyncMock()
                    mock_response.status_code = 409  # Conflict
                    
                    mock_client.return_value.__aenter__.return_value.put.return_value = mock_response
                    
                    response = client.post(
                        "/api/oauth/yandex/1/create-folder",
                        params={"folder_path": "/ExistingFolder"}
                    )
                    
                    assert response.status_code == 409
                    assert "already exists" in response.json()["detail"]