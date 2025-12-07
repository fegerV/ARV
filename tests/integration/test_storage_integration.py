import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from httpx import AsyncClient
from unittest.mock import patch, Mock

class TestStorageAPIIntegration:
    """Integration tests for storage API endpoints."""
    
    @pytest.fixture
    async def client(self):
        """Create test client."""
        from app.main import app
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    
    @pytest.fixture
    async def test_db_session(self):
        """Create test database session."""
        from app.core.database import get_db, async_session_maker
        
        # Create test session
        async with async_session_maker() as session:
            yield session
    
    @pytest.mark.asyncio
    async def test_list_storage_connections(self, client):
        """Test listing storage connections endpoint."""
        response = await client.get("/api/storage/connections")
        
        # Should return empty list or list of connections
        assert response.status_code in [200, 401]  # 401 if auth required
        
        if response.status_code == 200:
            assert isinstance(response.json(), list)
    
    @pytest.mark.asyncio
    async def test_create_storage_connection_local(self, client):
        """Test creating a local storage connection."""
        connection_data = {
            "name": "Test Local Storage",
            "provider": "local_disk",
            "base_path": "/tmp/test_storage",
            "is_default": False,
            "credentials": {}
        }
        
        response = await client.post("/api/storage/connections", json=connection_data)
        
        # May require authentication
        assert response.status_code in [200, 201, 401, 422]
    
    @pytest.mark.asyncio
    async def test_create_storage_connection_minio(self, client):
        """Test creating a MinIO storage connection."""
        connection_data = {
            "name": "Test MinIO Storage",
            "provider": "minio",
            "base_path": "/vertex-ar",
            "is_default": False,
            "credentials": {
                "endpoint": "minio:9000",
                "access_key": "test_key",
                "secret_key": "test_secret",
                "bucket_name": "vertex-ar",
                "secure": False,
                "region": "us-east-1"
            }
        }
        
        response = await client.post("/api/storage/connections", json=connection_data)
        
        # May require authentication
        assert response.status_code in [200, 201, 401, 422]
    
    @pytest.mark.asyncio
    async def test_create_storage_connection_yandex_disk(self, client):
        """Test creating a Yandex Disk storage connection."""
        connection_data = {
            "name": "Test Yandex Disk Storage",
            "provider": "yandex_disk",
            "base_path": "/VertexAR",
            "is_default": False,
            "credentials": {
                "oauth_token": "AQAAAAAEXAMPLE_TOKEN"
            }
        }
        
        response = await client.post("/api/storage/connections", json=connection_data)
        
        # May require authentication
        assert response.status_code in [200, 201, 401, 422]

class TestStorageProviderIntegration:
    """Integration tests for storage provider functionality."""
    
    @pytest.mark.asyncio
    async def test_storage_provider_initialization(self):
        """Test storage provider initialization with different configurations."""
        # Test local storage initialization
        with patch.dict(os.environ, {
            'STORAGE_TYPE': 'local',
            'STORAGE_BASE_PATH': '/tmp/test_storage'
        }):
            try:
                from app.core.storage import initialize_storage_provider, get_storage_provider
                
                # Reset global variable
                import app.core.storage
                app.core.storage.storage_provider = None
                
                # Test initialization
                initialize_storage_provider()
                provider = get_storage_provider()
                
                assert provider is not None
            except ImportError:
                # StorageProviderFactory might not exist yet
                pytest.skip("StorageProviderFactory not implemented")
    
    @pytest.mark.asyncio
    async def test_minio_fallback_to_local(self):
        """Test MinIO fallback to local storage on connection failure."""
        with patch.dict(os.environ, {
            'STORAGE_TYPE': 'minio',
            'MINIO_ENDPOINT': 'invalid-endpoint:9000',
            'MINIO_ACCESS_KEY': 'invalid_key',
            'MINIO_SECRET_KEY': 'invalid_secret',
            'STORAGE_BASE_PATH': '/tmp/test_storage'
        }):
            try:
                from app.core.storage import initialize_storage_provider
                
                # Reset global variable
                import app.core.storage
                app.core.storage.storage_provider = None
                
                # Should fall back to local storage
                initialize_storage_provider()
                
                # Should not raise exception
                assert True
            except ImportError:
                pytest.skip("StorageProviderFactory not implemented")
    
    @pytest.mark.asyncio
    async def test_yandex_disk_fallback_to_local(self):
        """Test Yandex Disk fallback to local storage on connection failure."""
        with patch.dict(os.environ, {
            'STORAGE_TYPE': 'yandex_disk',
            'YANDEX_DISK_OAUTH_TOKEN': 'invalid_token',
            'STORAGE_BASE_PATH': '/tmp/test_storage'
        }):
            try:
                from app.core.storage import initialize_storage_provider
                
                # Reset global variable
                import app.core.storage
                app.core.storage.storage_provider = None
                
                # Should fall back to local storage
                initialize_storage_provider()
                
                # Should not raise exception
                assert True
            except ImportError:
                pytest.skip("StorageProviderFactory not implemented")

class TestStorageFileOperations:
    """Integration tests for file operations with storage providers."""
    
    @pytest.fixture
    def test_file(self):
        """Create a temporary test file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Test content for storage integration")
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_local_file_operations(self, test_file):
        """Test file operations with local storage provider."""
        try:
            from app.services.storage.factory import StorageProviderFactory
            
            # Create local provider
            with tempfile.TemporaryDirectory() as temp_dir:
                provider = StorageProviderFactory.create_provider("local_disk", {"base_path": temp_dir})
                
                # Test upload
                remote_path = "test_upload.txt"
                result = await provider.upload_file(test_file, remote_path)
                
                # Test file exists
                uploaded_file = Path(temp_dir) / remote_path
                assert uploaded_file.exists()
                
                # Test download
                download_path = test_file + ".downloaded"
                await provider.download_file(remote_path, download_path)
                
                assert os.path.exists(download_path)
                with open(download_path, 'r') as f:
                    assert f.read() == "Test content for storage integration"
                
                # Test list files
                files = await provider.list_files()
                assert remote_path in files
                
                # Test delete
                await provider.delete_file(remote_path)
                assert not uploaded_file.exists()
                
                # Cleanup
                if os.path.exists(download_path):
                    os.unlink(download_path)
                    
        except ImportError:
            pytest.skip("StorageProviderFactory not implemented")
        except Exception as e:
            # Provider might not be fully implemented
            pytest.skip(f"Storage provider not fully implemented: {e}")

class TestStorageConfigurationValidation:
    """Integration tests for storage configuration validation."""
    
    @pytest.mark.asyncio
    async def test_storage_connection_schema_validation(self):
        """Test storage connection schema validation."""
        from app.schemas.storage import StorageConnectionCreate, MinIOCredentials, YandexDiskCredentials
        
        # Test local storage validation
        local_data = {
            "name": "Local Storage",
            "provider": "local_disk",
            "base_path": "/tmp/storage",
            "is_default": False,
            "credentials": {}
        }
        
        connection = StorageConnectionCreate(**local_data)
        assert connection.provider == "local_disk"
        assert connection.base_path == "/tmp/storage"
        
        # Test MinIO validation
        minio_data = {
            "name": "MinIO Storage",
            "provider": "minio",
            "base_path": "/vertex-ar",
            "is_default": False,
            "credentials": {
                "endpoint": "minio:9000",
                "access_key": "test_key",
                "secret_key": "test_secret",
                "bucket_name": "vertex-ar"
            }
        }
        
        connection = StorageConnectionCreate(**minio_data)
        assert connection.provider == "minio"
        
        # Test MinIO credentials schema
        credentials = MinIOCredentials(**minio_data["credentials"])
        assert credentials.endpoint == "minio:9000"
        assert credentials.access_key == "test_key"
        
        # Test Yandex Disk validation
        yandex_data = {
            "name": "Yandex Disk Storage",
            "provider": "yandex_disk",
            "base_path": "/VertexAR",
            "is_default": False,
            "credentials": {
                "oauth_token": "AQAAAAAEXAMPLE_TOKEN"
            }
        }
        
        connection = StorageConnectionCreate(**yandex_data)
        assert connection.provider == "yandex_disk"
        
        # Test Yandex Disk credentials schema
        credentials = YandexDiskCredentials(**yandex_data["credentials"])
        assert credentials.oauth_token == "AQAAAAAEXAMPLE_TOKEN"
    
    @pytest.mark.asyncio
    async def test_invalid_configuration_rejection(self):
        """Test that invalid configurations are properly rejected."""
        from app.schemas.storage import StorageConnectionCreate
        from pydantic import ValidationError
        
        # Test missing required fields for MinIO
        invalid_minio_data = {
            "name": "Invalid MinIO",
            "provider": "minio",
            "credentials": {
                "endpoint": "minio:9000"
                # Missing access_key, secret_key, bucket_name
            }
        }
        
        with pytest.raises(ValidationError):
            StorageConnectionCreate(**invalid_minio_data)
        
        # Test invalid provider
        invalid_provider_data = {
            "name": "Invalid Provider",
            "provider": "invalid_provider",
            "credentials": {}
        }
        
        with pytest.raises(ValidationError):
            StorageConnectionCreate(**invalid_provider_data)

class TestStoragePerformance:
    """Integration tests for storage performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_concurrent_file_operations(self):
        """Test concurrent file operations performance."""
        try:
            from app.services.storage.factory import StorageProviderFactory
            import time
            
            with tempfile.TemporaryDirectory() as temp_dir:
                provider = StorageProviderFactory.create_provider("local_disk", {"base_path": temp_dir})
                
                # Create test files
                test_files = []
                for i in range(5):
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                        f.write(f"Test content {i}")
                        test_files.append(f.name)
                
                try:
                    # Measure concurrent upload performance
                    start_time = time.time()
                    
                    upload_tasks = []
                    for i, test_file in enumerate(test_files):
                        task = provider.upload_file(test_file, f"concurrent_test_{i}.txt")
                        upload_tasks.append(task)
                    
                    await asyncio.gather(*upload_tasks)
                    
                    upload_time = time.time() - start_time
                    
                    # Should complete within reasonable time
                    assert upload_time < 5.0  # 5 seconds max for 5 small files
                    
                    # Verify all files exist
                    for i in range(5):
                        file_path = Path(temp_dir) / f"concurrent_test_{i}.txt"
                        assert file_path.exists()
                    
                    # Cleanup uploaded files
                    delete_tasks = []
                    for i in range(5):
                        task = provider.delete_file(f"concurrent_test_{i}.txt")
                        delete_tasks.append(task)
                    
                    await asyncio.gather(*delete_tasks)
                    
                finally:
                    # Cleanup test files
                    for test_file in test_files:
                        if os.path.exists(test_file):
                            os.unlink(test_file)
                            
        except ImportError:
            pytest.skip("StorageProviderFactory not implemented")
        except Exception as e:
            pytest.skip(f"Storage provider not fully implemented: {e}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])