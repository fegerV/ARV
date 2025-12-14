"""
Unit tests for storage provider factory.

This test file replaces the old storage factory tests with tests for the new
simplified storage provider system.
"""

import pytest
from unittest.mock import patch

from app.core.storage_providers import get_storage_provider, LocalStorageProvider, reset_storage_provider


class TestStorageProviderFactory:
    """Test cases for the simplified storage provider factory."""

    def test_get_storage_provider_returns_local(self):
        """Test that get_storage_provider returns LocalStorageProvider by default."""
        with patch('app.core.storage_providers.settings.LOCAL_STORAGE_PATH', '/tmp/test_default'):
            reset_storage_provider()
            
            provider = get_storage_provider()
            
            assert isinstance(provider, LocalStorageProvider)

    @patch('app.core.storage_providers.settings.LOCAL_STORAGE_PATH', '/tmp/custom/storage')
    @patch('app.core.storage_providers.settings.LOCAL_STORAGE_PUBLIC_URL', 'http://custom.com/storage')
    def test_get_storage_provider_uses_settings(self):
        """Test that get_storage_provider uses configuration settings."""
        reset_storage_provider()
        
        provider = get_storage_provider()
        
        assert isinstance(provider, LocalStorageProvider)
        assert str(provider.base_path) == '/tmp/custom/storage'
        assert provider.public_url_base == 'http://custom.com/storage'

    def test_get_storage_provider_singleton(self):
        """Test that get_storage_provider returns the same instance."""
        with patch('app.core.storage_providers.settings.LOCAL_STORAGE_PATH', '/tmp/test_singleton'):
            reset_storage_provider()
            
            provider1 = get_storage_provider()
            provider2 = get_storage_provider()
            
            assert provider1 is provider2

    def test_reset_storage_provider(self):
        """Test reset_storage_provider creates new instances."""
        with patch('app.core.storage_providers.settings.LOCAL_STORAGE_PATH', '/tmp/test_reset'):
            provider1 = get_storage_provider()
            
            reset_storage_provider()
            provider2 = get_storage_provider()
            
            assert provider1 is not provider2
            assert isinstance(provider2, LocalStorageProvider)


class TestStorageProviderConfiguration:
    """Test cases for storage provider configuration."""

    @patch('app.core.storage_providers.settings')
    def test_local_storage_provider_initialization(self, mock_settings):
        """Test LocalStorageProvider initialization with custom settings."""
        mock_settings.LOCAL_STORAGE_PATH = '/tmp/test/storage/path'
        mock_settings.LOCAL_STORAGE_PUBLIC_URL = 'http://test.com/storage'
        
        reset_storage_provider()
        provider = get_storage_provider()
        
        assert str(provider.base_path) == '/tmp/test/storage/path'
        assert provider.public_url_base == 'http://test.com/storage'

    def test_local_storage_provider_default_settings(self):
        """Test LocalStorageProvider uses default settings when none provided."""
        with patch('app.core.storage_providers.settings.LOCAL_STORAGE_PATH', '/tmp/test_default'):
            reset_storage_provider()
            provider = get_storage_provider()
            
            # Should use defaults from settings
            assert provider.base_path.exists()  # Base directory should be created
            assert provider.public_url_base is not None