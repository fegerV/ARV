"""
Unit tests for storage providers.

Tests cover the local storage provider implementation including file operations,
URL generation, usage statistics, and error handling.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, AsyncMock

from app.core.storage_providers import LocalStorageProvider, get_storage_provider, reset_storage_provider
from app.core.config import settings


class TestLocalStorageProvider:
    """Test cases for LocalStorageProvider."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def storage_provider(self, temp_dir):
        """Create a LocalStorageProvider instance with temp directory."""
        return LocalStorageProvider(
            base_path=str(temp_dir),
            public_url_base="http://test.com/storage"
        )

    @pytest.fixture
    def sample_file(self, temp_dir):
        """Create a sample file for testing."""
        file_path = temp_dir / "test_file.txt"
        file_path.write_text("Hello, World!")
        return file_path

    @pytest.mark.asyncio
    async def test_save_file(self, storage_provider, sample_file, temp_dir):
        """Test saving a file to storage."""
        # Save file
        destination_path = "test_dir/saved_file.txt"
        public_url = await storage_provider.save_file(
            source_path=str(sample_file),
            destination_path=destination_path
        )

        # Verify file was saved
        saved_file = temp_dir / "test_dir" / "saved_file.txt"
        assert saved_file.exists()
        assert saved_file.read_text() == "Hello, World!"

        # Verify public URL
        assert public_url == "http://test.com/storage/test_dir/saved_file.txt"

    @pytest.mark.asyncio
    async def test_save_file_creates_directories(self, storage_provider, sample_file, temp_dir):
        """Test that save_file creates intermediate directories."""
        destination_path = "nested/deep/path/file.txt"
        
        await storage_provider.save_file(
            source_path=str(sample_file),
            destination_path=destination_path
        )

        # Verify nested directories were created
        nested_dir = temp_dir / "nested" / "deep" / "path"
        assert nested_dir.exists()
        assert nested_dir.is_dir()

    @pytest.mark.asyncio
    async def test_save_file_source_not_exists(self, storage_provider):
        """Test save_file with non-existent source file."""
        with pytest.raises(FileNotFoundError):
            await storage_provider.save_file(
                source_path="/non/existent/file.txt",
                destination_path="test.txt"
            )

    @pytest.mark.asyncio
    async def test_get_file(self, storage_provider, temp_dir):
        """Test retrieving a file from storage."""
        # Create a file in storage
        storage_file = temp_dir / "storage_file.txt"
        storage_file.write_text("Storage content")
        
        # Retrieve file
        local_file = temp_dir / "retrieved_file.txt"
        success = await storage_provider.get_file(
            storage_path="storage_file.txt",
            local_path=str(local_file)
        )

        assert success
        assert local_file.exists()
        assert local_file.read_text() == "Storage content"

    @pytest.mark.asyncio
    async def test_get_file_not_exists(self, storage_provider, temp_dir):
        """Test retrieving a non-existent file."""
        local_file = temp_dir / "retrieved_file.txt"
        success = await storage_provider.get_file(
            storage_path="non_existent.txt",
            local_path=str(local_file)
        )

        assert not success
        assert not local_file.exists()

    @pytest.mark.asyncio
    async def test_delete_file(self, storage_provider, temp_dir):
        """Test deleting a file from storage."""
        # Create a file in storage
        storage_file = temp_dir / "to_delete.txt"
        storage_file.write_text("Delete me")
        
        # Delete file
        success = await storage_provider.delete_file("to_delete.txt")
        
        assert success
        assert not storage_file.exists()

    @pytest.mark.asyncio
    async def test_delete_file_not_exists(self, storage_provider):
        """Test deleting a non-existent file."""
        success = await storage_provider.delete_file("non_existent.txt")
        assert not success

    @pytest.mark.asyncio
    async def test_delete_directory(self, storage_provider, temp_dir):
        """Test deleting a directory from storage."""
        # Create a directory with files
        test_dir = temp_dir / "test_dir"
        test_dir.mkdir()
        (test_dir / "file1.txt").write_text("Content 1")
        (test_dir / "file2.txt").write_text("Content 2")
        
        # Delete directory
        success = await storage_provider.delete_file("test_dir")
        
        assert success
        assert not test_dir.exists()

    @pytest.mark.asyncio
    async def test_file_exists(self, storage_provider, temp_dir):
        """Test checking if a file exists."""
        # Create a file
        (temp_dir / "exists.txt").write_text("Exists")
        
        # Test existing file
        assert await storage_provider.file_exists("exists.txt")
        
        # Test non-existent file
        assert not await storage_provider.file_exists("non_existent.txt")

    def test_get_public_url(self, storage_provider):
        """Test generating public URLs."""
        url = storage_provider.get_public_url("test/path/file.txt")
        assert url == "http://test.com/storage/test/path/file.txt"

    def test_get_public_url_normalizes_path(self, storage_provider):
        """Test that get_public_url normalizes paths with leading slashes."""
        url1 = storage_provider.get_public_url("test/file.txt")
        url2 = storage_provider.get_public_url("/test/file.txt")
        
        assert url1 == url2 == "http://test.com/storage/test/file.txt"

    @pytest.mark.asyncio
    async def test_get_usage_stats_empty_directory(self, storage_provider, temp_dir):
        """Test getting usage stats for empty directory."""
        stats = await storage_provider.get_usage_stats()
        
        assert stats["total_files"] == 0
        assert stats["total_size_bytes"] == 0
        assert stats["total_size_mb"] == 0.0
        assert stats["exists"] is True
        assert stats["path"] == str(temp_dir)

    @pytest.mark.asyncio
    async def test_get_usage_stats_with_files(self, storage_provider, temp_dir):
        """Test getting usage stats for directory with files."""
        # Create test files
        (temp_dir / "file1.txt").write_text("Hello")  # 5 bytes
        (temp_dir / "file2.txt").write_text("World!")  # 6 bytes
        
        # Create subdirectory with file
        sub_dir = temp_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file3.txt").write_text("Test")  # 4 bytes
        
        stats = await storage_provider.get_usage_stats()
        
        assert stats["total_files"] == 3
        assert stats["total_size_bytes"] == 15  # 5 + 6 + 4
        assert abs(stats["total_size_mb"] - (15 / (1024 * 1024))) < 0.0001

    @pytest.mark.asyncio
    async def test_get_usage_stats_specific_path(self, storage_provider, temp_dir):
        """Test getting usage stats for specific path."""
        # Create files
        (temp_dir / "root_file.txt").write_text("Root")
        
        sub_dir = temp_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "sub_file.txt").write_text("Sub")
        
        # Get stats for subdirectory
        stats = await storage_provider.get_usage_stats("subdir")
        
        assert stats["total_files"] == 1
        assert stats["total_size_bytes"] == 3  # len("Sub")
        assert stats["path"] == str(sub_dir)

    @pytest.mark.asyncio
    async def test_get_usage_stats_non_existent_path(self, storage_provider):
        """Test getting usage stats for non-existent path."""
        stats = await storage_provider.get_usage_stats("non_existent")
        
        assert stats["total_files"] == 0
        assert stats["total_size_bytes"] == 0
        assert stats["exists"] is False

    @pytest.mark.asyncio
    async def test_get_usage_stats_single_file(self, storage_provider, temp_dir):
        """Test getting usage stats for a single file."""
        # Create a file
        test_file = temp_dir / "single_file.txt"
        test_file.write_text("Single file content")
        
        stats = await storage_provider.get_usage_stats("single_file.txt")
        
        assert stats["total_files"] == 1
        assert stats["total_size_bytes"] == test_file.stat().st_size
        assert stats["exists"] is True

    def test_get_full_path_security(self, storage_provider, temp_dir):
        """Test that _get_full_path prevents directory traversal."""
        # Test normal path
        full_path = storage_provider._get_full_path("test/file.txt")
        assert full_path == temp_dir / "test" / "file.txt"
        
        # Test path traversal attempt (should be contained within base_path)
        full_path = storage_provider._get_full_path("../../../etc/passwd")
        assert temp_dir in full_path.parents
        assert full_path == temp_dir / ".." / ".." / ".." / "etc" / "passwd"
        
        # Test leading slash normalization
        full_path = storage_provider._get_full_path("/test/file.txt")
        assert full_path == temp_dir / "test" / "file.txt"


class TestStorageProviderFactory:
    """Test cases for storage provider factory functions."""

    def test_get_storage_provider_singleton(self):
        """Test that get_storage_provider returns the same instance."""
        with patch('app.core.storage_providers.settings.LOCAL_STORAGE_PATH', '/tmp/test_singleton'):
            reset_storage_provider()
            
            provider1 = get_storage_provider()
            provider2 = get_storage_provider()
            
            assert provider1 is provider2
            assert isinstance(provider1, LocalStorageProvider)

    @patch('app.core.storage_providers.settings')
    def test_get_storage_provider_uses_settings(self, mock_settings):
        """Test get_storage_provider uses settings when available."""
        mock_settings.LOCAL_STORAGE_PATH = "/tmp/test_storage"
        mock_settings.LOCAL_STORAGE_PUBLIC_URL = "http://test.com/storage"
        
        reset_storage_provider()
        provider = get_storage_provider()
        
        assert isinstance(provider, LocalStorageProvider)
        assert str(provider.base_path) == "/tmp/test_storage"
        assert provider.public_url_base == "http://test.com/storage"

    def test_reset_storage_provider(self):
        """Test reset_storage_provider function."""
        with patch('app.core.storage_providers.settings.LOCAL_STORAGE_PATH', '/tmp/test_reset'):
            # Get a provider
            provider1 = get_storage_provider()
            
            # Reset and get another
            reset_storage_provider()
            provider2 = get_storage_provider()
            
            # Should be different instances
            assert provider1 is not provider2
            assert isinstance(provider2, LocalStorageProvider)


class TestStorageProviderIntegration:
    """Integration tests for storage provider with real file operations."""

    @pytest.fixture
    def integration_temp_dir(self):
        """Create a temporary directory for integration tests."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_complete_file_workflow(self, integration_temp_dir):
        """Test complete workflow: save -> exists -> get -> delete."""
        provider = LocalStorageProvider(
            base_path=str(integration_temp_dir),
            public_url_base="http://test.com/storage"
        )
        
        # Create source file
        source_file = integration_temp_dir / "source.txt"
        source_file.write_text("Integration test content")
        
        # Save to storage
        storage_path = "integration/test.txt"
        public_url = await provider.save_file(str(source_file), storage_path)
        
        assert public_url == "http://test.com/storage/integration/test.txt"
        assert await provider.file_exists(storage_path)
        
        # Get from storage
        retrieved_file = integration_temp_dir / "retrieved.txt"
        success = await provider.get_file(storage_path, str(retrieved_file))
        
        assert success
        assert retrieved_file.read_text() == "Integration test content"
        
        # Delete from storage
        delete_success = await provider.delete_file(storage_path)
        assert delete_success
        assert not await provider.file_exists(storage_path)

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, integration_temp_dir):
        """Test concurrent storage operations."""
        import asyncio
        
        provider = LocalStorageProvider(
            base_path=str(integration_temp_dir),
            public_url_base="http://test.com/storage"
        )
        
        # Create multiple source files
        source_files = []
        for i in range(5):
            source_file = integration_temp_dir / f"source_{i}.txt"
            source_file.write_text(f"Content {i}")
            source_files.append(source_file)
        
        # Concurrent save operations
        async def save_file(source_file, index):
            return await provider.save_file(
                str(source_file), 
                f"concurrent/file_{index}.txt"
            )
        
        tasks = [save_file(sf, i) for i, sf in enumerate(source_files)]
        urls = await asyncio.gather(*tasks)
        
        # Verify all files were saved
        assert len(urls) == 5
        for i, url in enumerate(urls):
            assert url == f"http://test.com/storage/concurrent/file_{i}.txt"
            assert await provider.file_exists(f"concurrent/file_{i}.txt")