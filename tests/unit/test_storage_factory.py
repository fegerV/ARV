import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.services.storage.factory import get_provider
from app.services.storage.local_provider import LocalStorageProvider
from app.services.storage.minio_provider import MinioStorageProvider
from app.services.storage.yandex_disk_provider import YandexDiskProvider


class TestStorageFactory(unittest.TestCase):
    """Test cases for storage provider factory"""

    def test_get_local_provider(self):
        """Test getting LocalStorageProvider"""
        # Create a mock StorageConnection
        mock_connection = Mock()
        mock_connection.provider = "local_disk"
        mock_connection.base_path = "/test/path"
        mock_connection.endpoint = None
        mock_connection.access_key = None
        mock_connection.secret_key = None
        mock_connection.secure = False
        mock_connection.bucket = None
        mock_connection.token = None
        
        # Get provider
        provider = get_provider(mock_connection)
        
        # Check that we got the right type
        self.assertIsInstance(provider, LocalStorageProvider)
        self.assertEqual(provider.base_path, "/test/path")

    @patch('minio.Minio')
    def test_get_minio_provider(self, mock_minio):
        """Test getting MinioStorageProvider"""
        # Create a mock StorageConnection
        mock_connection = Mock()
        mock_connection.provider = "minio"
        mock_connection.base_path = None
        mock_connection.endpoint = "localhost:9000"
        mock_connection.access_key = "test_access_key"
        mock_connection.secret_key = "test_secret_key"
        mock_connection.secure = False
        mock_connection.bucket = "test-bucket"
        mock_connection.token = None
        
        # Mock the Minio client
        mock_client = Mock()
        mock_minio.return_value = mock_client
        mock_client.bucket_exists.return_value = True
        
        # Get provider
        provider = get_provider(mock_connection)
        
        # Check that we got the right type
        self.assertIsInstance(provider, MinioStorageProvider)
        self.assertEqual(provider.bucket, "test-bucket")
        
        # Check that Minio was called with correct parameters
        mock_minio.assert_called_once_with(
            "localhost:9000",
            access_key="test_access_key",
            secret_key="test_secret_key",
            secure=False
        )

    def test_get_yandex_disk_provider(self):
        """Test getting YandexDiskProvider"""
        # Create a mock StorageConnection
        mock_connection = Mock()
        mock_connection.provider = "yandex_disk"
        mock_connection.base_path = "/test"
        mock_connection.endpoint = None
        mock_connection.access_key = None
        mock_connection.secret_key = None
        mock_connection.secure = False
        mock_connection.bucket = None
        mock_connection.token = "test_token"
        
        # Get provider
        provider = get_provider(mock_connection)
        
        # Check that we got the right type
        self.assertIsInstance(provider, YandexDiskProvider)
        self.assertEqual(provider.token, "test_token")
        self.assertEqual(provider.base_path, "/test")

    def test_get_unsupported_provider(self):
        """Test getting unsupported provider raises ValueError"""
        # Create a mock StorageConnection with unsupported provider
        mock_connection = Mock()
        mock_connection.provider = "unsupported_provider"
        
        # Check that ValueError is raised
        with self.assertRaises(ValueError) as context:
            get_provider(mock_connection)
        
        self.assertIn("Unsupported storage provider", str(context.exception))


if __name__ == '__main__':
    unittest.main()