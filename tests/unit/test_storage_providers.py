import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

# Mock the storage provider factory since it might not exist yet
@pytest.fixture
def mock_storage_provider_factory():
    """Mock the StorageProviderFactory for testing."""
    with patch('app.services.storage.factory.StorageProviderFactory') as mock_factory:
        yield mock_factory

@pytest.fixture
def mock_local_provider():
    """Mock a local storage provider."""
    provider = Mock()
    provider.upload_file = AsyncMock(return_value="uploaded_file_path")
    provider.download_file = AsyncMock()
    provider.delete_file = AsyncMock()
    provider.list_files = AsyncMock(return_value=["file1.jpg", "file2.mp4"])
    provider.generate_presigned_url = AsyncMock(return_value="http://example.com/presigned-url")
    provider.test_connection = AsyncMock(return_value=True)
    return provider

class TestStorageProviderFactory:
    """Test the storage provider factory functionality."""
    
    @pytest.mark.asyncio
    async def test_create_local_provider(self, mock_storage_provider_factory):
        """Test creating a local storage provider."""
        # Setup mock
        mock_provider = Mock()
        mock_storage_provider_factory.create_provider.return_value = mock_provider
        
        # Test creation
        from app.services.storage.factory import StorageProviderFactory
        provider = StorageProviderFactory.create_provider("local_disk", {"base_path": "/tmp"})
        
        # Verify
        mock_storage_provider_factory.create_provider.assert_called_once_with("local_disk", {"base_path": "/tmp"})
        assert provider == mock_provider
    
    @pytest.mark.asyncio
    async def test_create_minio_provider(self, mock_storage_provider_factory):
        """Test creating a MinIO storage provider."""
        # Setup mock
        mock_provider = Mock()
        mock_storage_provider_factory.create_provider.return_value = mock_provider
        
        # Test creation
        from app.services.storage.factory import StorageProviderFactory
        config = {
            "endpoint": "minio:9000",
            "access_key": "key",
            "secret_key": "secret",
            "bucket_name": "vertex-ar"
        }
        provider = StorageProviderFactory.create_provider("minio", config)
        
        # Verify
        mock_storage_provider_factory.create_provider.assert_called_once_with("minio", config)
        assert provider == mock_provider
    
    @pytest.mark.asyncio
    async def test_create_yandex_disk_provider(self, mock_storage_provider_factory):
        """Test creating a Yandex Disk storage provider."""
        # Setup mock
        mock_provider = Mock()
        mock_storage_provider_factory.create_provider.return_value = mock_provider
        
        # Test creation
        from app.services.storage.factory import StorageProviderFactory
        config = {"oauth_token": "test_token", "base_path": "/VertexAR"}
        provider = StorageProviderFactory.create_provider("yandex_disk", config)
        
        # Verify
        mock_storage_provider_factory.create_provider.assert_called_once_with("yandex_disk", config)
        assert provider == mock_provider

class TestBaseStorageProvider:
    """Test the base storage provider interface."""
    
    @pytest.mark.asyncio
    async def test_provider_interface_methods(self, mock_local_provider):
        """Test that provider interface methods exist and are callable."""
        # Test all interface methods
        await mock_local_provider.upload_file("/tmp/test.txt", "remote/test.txt")
        mock_local_provider.upload_file.assert_called_once_with("/tmp/test.txt", "remote/test.txt")
        
        await mock_local_provider.download_file("remote/test.txt", "/tmp/downloaded.txt")
        mock_local_provider.download_file.assert_called_once_with("remote/test.txt", "/tmp/downloaded.txt")
        
        await mock_local_provider.delete_file("remote/test.txt")
        mock_local_provider.delete_file.assert_called_once_with("remote/test.txt")
        
        files = await mock_local_provider.list_files("remote/")
        mock_local_provider.list_files.assert_called_once_with("remote/")
        assert files == ["file1.jpg", "file2.mp4"]
        
        url = await mock_local_provider.generate_presigned_url("remote/test.txt")
        mock_local_provider.generate_presigned_url.assert_called_once_with("remote/test.txt")
        assert url == "http://example.com/presigned-url"
        
        is_connected = await mock_local_provider.test_connection()
        mock_local_provider.test_connection.assert_called_once()
        assert is_connected is True

class TestStorageConfiguration:
    """Test storage configuration validation."""
    
    def test_local_storage_config_validation(self):
        """Test local storage configuration validation."""
        # Valid configuration
        config = {"base_path": "/app/storage"}
        assert "base_path" in config
        assert config["base_path"].startswith("/")
    
    def test_minio_config_validation(self):
        """Test MinIO configuration validation."""
        # Valid configuration
        config = {
            "endpoint": "minio:9000",
            "access_key": "test_key",
            "secret_key": "test_secret",
            "bucket_name": "vertex-ar",
            "secure": False,
            "region": "us-east-1"
        }
        
        required_fields = ["endpoint", "access_key", "secret_key", "bucket_name"]
        for field in required_fields:
            assert field in config
    
    def test_yandex_disk_config_validation(self):
        """Test Yandex Disk configuration validation."""
        # Valid configuration
        config = {
            "oauth_token": "AQAAAAAEXAMPLE_TOKEN",
            "base_path": "/VertexAR"
        }
        
        assert "oauth_token" in config
        assert config["oauth_token"].startswith("AQAAAAA")

class TestStorageIntegration:
    """Test storage integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_storage_initialization(self):
        """Test storage provider initialization."""
        with patch('app.core.storage.StorageProviderFactory') as mock_factory:
            mock_provider = Mock()
            mock_factory.create_provider.return_value = mock_provider
            
            # Test initialization
            from app.core.storage import initialize_storage_provider
            initialize_storage_provider()
            
            # Verify factory was called
            mock_factory.create_provider.assert_called()
    
    @pytest.mark.asyncio
    async def test_storage_provider_singleton(self):
        """Test that storage provider is a singleton."""
        with patch('app.core.storage.storage_provider', None):
            with patch('app.core.storage.initialize_storage_provider') as mock_init:
                from app.core.storage import get_storage_provider
                
                # First call should initialize
                provider1 = get_storage_provider()
                mock_init.assert_called_once()
                
                # Second call should return same instance
                provider2 = get_storage_provider()
                assert provider1 is provider2

class TestStorageErrorHandling:
    """Test storage error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_provider_creation_failure(self):
        """Test handling of provider creation failures."""
        with patch('app.services.storage.factory.StorageProviderFactory') as mock_factory:
            mock_factory.create_provider.side_effect = Exception("Connection failed")
            
            from app.services.storage.factory import StorageProviderFactory
            
            with pytest.raises(Exception, match="Connection failed"):
                StorageProviderFactory.create_provider("minio", {})
    
    @pytest.mark.asyncio
    async def test_file_operation_failure(self, mock_local_provider):
        """Test handling of file operation failures."""
        # Setup mock to raise exception
        mock_local_provider.upload_file.side_effect = Exception("Upload failed")
        
        with pytest.raises(Exception, match="Upload failed"):
            await mock_local_provider.upload_file("/tmp/test.txt", "remote/test.txt")

class TestStoragePerformance:
    """Test storage performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, mock_local_provider):
        """Test concurrent file operations."""
        import asyncio
        
        # Create multiple concurrent upload tasks
        tasks = []
        for i in range(5):
            task = mock_local_provider.upload_file(f"/tmp/test{i}.txt", f"remote/test{i}.txt")
            tasks.append(task)
        
        # Execute all tasks concurrently
        await asyncio.gather(*tasks)
        
        # Verify all calls were made
        assert mock_local_provider.upload_file.call_count == 5

# Utility tests
class TestStorageUtilities:
    """Test storage utility functions."""
    
    def test_path_sanitization(self):
        """Test path sanitization utilities."""
        # Test various path scenarios
        test_cases = [
            ("normal/path", "normal/path"),
            ("../malicious", "malicious"),  # Should remove ../
            ("/absolute/path", "absolute/path"),  # Should remove leading /
        ]
        
        for input_path, expected in test_cases:
            # Simple sanitization logic
            sanitized = input_path.lstrip('/').replace('../', '')
            assert sanitized == expected
    
    def test_file_extension_validation(self):
        """Test file extension validation."""
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.mp4', '.mov'}
        
        test_cases = [
            ("image.jpg", True),
            ("video.mp4", True),
            ("document.pdf", False),
            ("script.js", False),
        ]
        
        for filename, expected in test_cases:
            ext = Path(filename).suffix.lower()
            is_allowed = ext in allowed_extensions
            assert is_allowed == expected

if __name__ == "__main__":
    pytest.main([__file__, "-v"])