import unittest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.services.storage.local_provider import LocalStorageProvider
from app.services.storage.minio_provider import MinioStorageProvider
from app.services.storage.yandex_disk_provider import YandexDiskProvider


class TestLocalStorageProvider(unittest.TestCase):
    """Test cases for LocalStorageProvider"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.config = {"base_path": "/tmp/test_storage"}
        self.provider = LocalStorageProvider(self.config)
    
    def test_init(self):
        """Test LocalStorageProvider initialization"""
        self.assertIsInstance(self.provider, LocalStorageProvider)
        self.assertEqual(self.provider.base_path, "/tmp/test_storage")
        self.assertTrue(Path(self.provider.base_path).exists())
    
    def test_get_file_url(self):
        """Test get_file_url method"""
        url = asyncio.run(self.provider.get_file_url("test/file.jpg"))
        self.assertEqual(url, "/storage/content/test/file.jpg")


class TestMinioStorageProvider(unittest.TestCase):
    """Test cases for MinioStorageProvider"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.config = {
            "endpoint": "localhost:9000",
            "access_key": "test_access_key",
            "secret_key": "test_secret_key",
            "bucket": "test-bucket"
        }
    
    @patch('minio.Minio')
    def test_init(self, mock_minio):
        """Test MinioStorageProvider initialization"""
        mock_client = Mock()
        mock_minio.return_value = mock_client
        mock_client.bucket_exists.return_value = False
        
        provider = MinioStorageProvider(self.config)
        
        self.assertIsInstance(provider, MinioStorageProvider)
        mock_minio.assert_called_once_with(
            "localhost:9000",
            access_key="test_access_key",
            secret_key="test_secret_key",
            secure=False
        )
        mock_client.make_bucket.assert_called_once_with("test-bucket")
    
    @patch('minio.Minio')
    def test_get_file_url(self, mock_minio):
        """Test get_file_url method"""
        mock_client = Mock()
        mock_minio.return_value = mock_client
        mock_client.bucket_exists.return_value = True
        
        provider = MinioStorageProvider(self.config)
        url = asyncio.run(provider.get_file_url("test/file.jpg"))
        self.assertEqual(url, "https://localhost:9000/test-bucket/test/file.jpg")


class TestYandexDiskProvider(unittest.TestCase):
    """Test cases for YandexDiskProvider"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.config = {
            "token": "test_token",
            "base_path": "/test"
        }
        self.provider = YandexDiskProvider(self.config)
    
    def test_init(self):
        """Test YandexDiskProvider initialization"""
        self.assertIsInstance(self.provider, YandexDiskProvider)
        self.assertEqual(self.provider.token, "test_token")
        self.assertEqual(self.provider.base_path, "/test")
        self.assertEqual(self.provider.base_url, "https://cloud-api.yandex.net/v1/disk")
    
    def test_get_file_url(self):
        """Test get_file_url method"""
        url = asyncio.run(self.provider.get_file_url("test/file.jpg"))
        # Should return fallback URL since we're not actually calling the API
        self.assertTrue(url.startswith("https://disk.yandex.ru/i/"))


if __name__ == '__main__':
    unittest.main()