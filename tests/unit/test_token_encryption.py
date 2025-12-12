"""Unit tests for token encryption utilities."""

import pytest
import base64
import json
from unittest.mock import patch
from app.utils.token_encryption import TokenEncryption


@pytest.fixture
def token_enc():
    """Create a TokenEncryption instance for testing."""
    return TokenEncryption()


class TestTokenEncryption:
    """Test cases for TokenEncryption."""

    def test_init_with_valid_secret_key(self):
        """Test initialization with a valid SECRET_KEY."""
        with patch('app.utils.token_encryption.settings') as mock_settings:
            mock_settings.SECRET_KEY = "test-secret-key-that-is-long-enough-for-testing"
            encryption = TokenEncryption()
            assert encryption.is_encryption_available() is True

    def test_encrypt_decrypt_credentials(self, token_enc):
        """Test successful encryption and decryption of credentials."""
        credentials = {
            "oauth_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
            "token_type": "bearer",
        }
        
        # Encrypt
        encrypted = token_enc.encrypt_credentials(credentials)
        assert encrypted is not None
        assert encrypted != credentials
        
        # Decrypt
        decrypted = token_enc.decrypt_credentials(encrypted)
        assert decrypted == credentials

    def test_encrypt_decrypt_empty_credentials(self, token_enc):
        """Test encryption and decryption of empty credentials."""
        credentials = {}
        
        encrypted = token_enc.encrypt_credentials(credentials)
        decrypted = token_enc.decrypt_credentials(encrypted)
        
        assert decrypted == credentials

    def test_decrypt_invalid_data(self, token_enc):
        """Test decryption of invalid data."""
        # Test with completely invalid data
        result = token_enc.decrypt_credentials("invalid_base64_data")
        assert result == {}
        
        # Test with valid base64 but invalid JSON
        invalid_json = base64.b64encode(b"not valid json").decode()
        result = token_enc.decrypt_credentials(invalid_json)
        assert result == {}

    def test_decrypt_legacy_base64_data(self, token_enc):
        """Test decryption of legacy base64-encoded data."""
        credentials = {
            "oauth_token": "legacy_token",
            "refresh_token": "legacy_refresh",
        }
        
        # Create legacy format (base64 encoded JSON)
        legacy_data = base64.b64encode(json.dumps(credentials).encode()).decode()
        
        # Should decrypt successfully
        decrypted = token_enc.decrypt_credentials(legacy_data)
        assert decrypted == credentials

    def test_encryption_without_cipher(self):
        """Test encryption when cipher is not available."""
        with patch('app.utils.token_encryption.settings') as mock_settings:
            mock_settings.SECRET_KEY = "test-key"
            
            # Create instance and manually disable cipher
            encryption = TokenEncryption()
            encryption._cipher = None
            
            credentials = {"oauth_token": "test_token"}
            
            # Should fallback to base64 encoding
            encrypted = encryption.encrypt_credentials(credentials)
            assert encrypted is not None
            
            # Should be able to decrypt
            decrypted = encryption.decrypt_credentials(encrypted)
            assert decrypted == credentials

    def test_is_encryption_available(self, token_enc):
        """Test encryption availability check."""
        # This will depend on whether the cipher was successfully initialized
        # In most cases it should be available
        result = token_enc.is_encryption_available()
        assert isinstance(result, bool)

    def test_encrypt_decrypt_complex_credentials(self, token_enc):
        """Test encryption with complex credential structure."""
        credentials = {
            "oauth_token": "complex_access_token_with_special_chars_!@#$%^&*()",
            "refresh_token": "refresh_token_with_unicode_测试_🚀",
            "expires_in": 7200,
            "token_type": "bearer",
            "scope": ["read", "write", "admin"],
            "metadata": {
                "user_id": 12345,
                "permissions": ["cloud_api:disk.read", "cloud_api:disk.write"],
                "app_info": {"name": "Vertex AR", "version": "2.0.0"}
            },
            "created_at": "2023-12-01T10:00:00Z"
        }
        
        encrypted = token_enc.encrypt_credentials(credentials)
        decrypted = token_enc.decrypt_credentials(encrypted)
        
        assert decrypted == credentials

    def test_encrypt_decrypt_credentials_with_none_values(self, token_enc):
        """Test encryption and decryption with None values."""
        credentials = {
            "oauth_token": "test_token",
            "refresh_token": None,
            "expires_in": None,
            "token_type": "bearer",
            "metadata": None,
        }
        
        encrypted = token_enc.encrypt_credentials(credentials)
        decrypted = token_enc.decrypt_credentials(encrypted)
        
        assert decrypted == credentials

    def test_encrypt_decrypt_large_credentials(self, token_enc):
        """Test encryption and decryption of large credential data."""
        # Create a large credentials object
        credentials = {
            "oauth_token": "x" * 1000,  # Large token
            "refresh_token": "y" * 1000,  # Large refresh token
            "large_metadata": {"data": "z" * 5000}  # Large metadata
        }
        
        encrypted = token_enc.encrypt_credentials(credentials)
        decrypted = token_enc.decrypt_credentials(encrypted)
        
        assert decrypted == credentials

    def test_encryption_key_derivation_consistency(self):
        """Test that encryption key derivation is consistent."""
        with patch('app.utils.token_encryption.settings') as mock_settings:
            mock_settings.SECRET_KEY = "consistent-test-key-for-encryption-testing"
            
            encryption1 = TokenEncryption()
            encryption2 = TokenEncryption()
            
            credentials = {"test": "data"}
            
            encrypted1 = encryption1.encrypt_credentials(credentials)
            encrypted2 = encryption2.encrypt_credentials(credentials)
            
            # Both should produce the same encrypted data
            assert encrypted1 == encrypted2
            
            # Both should decrypt to the same original data
            decrypted1 = encryption1.decrypt_credentials(encrypted1)
            decrypted2 = encryption2.decrypt_credentials(encrypted2)
            
            assert decrypted1 == credentials
            assert decrypted2 == credentials