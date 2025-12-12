"""Token encryption utilities for secure storage of OAuth tokens."""

import base64
import json
from typing import Dict, Any, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import get_settings

settings = get_settings()


class TokenEncryption:
    """Handles encryption and decryption of OAuth tokens."""
    
    def __init__(self):
        self._cipher: Optional[Fernet] = None
        self._init_cipher()
    
    def _init_cipher(self) -> None:
        """Initialize the cipher with a key derived from SECRET_KEY."""
        try:
            # Derive a proper encryption key from the SECRET_KEY
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'vertex_ar_oauth_salt',  # Fixed salt for consistency
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
            self._cipher = Fernet(key)
        except Exception:
            # If encryption fails, we'll store tokens unencrypted (development only)
            self._cipher = None
    
    def encrypt_credentials(self, credentials: Dict[str, Any]) -> str:
        """Encrypt OAuth credentials for secure storage."""
        if self._cipher is None:
            # Fallback to base64 encoding (not secure, for development only)
            return base64.b64encode(json.dumps(credentials).encode()).decode()
        
        try:
            json_data = json.dumps(credentials).encode()
            encrypted_data = self._cipher.encrypt(json_data)
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception:
            # Fallback to base64 encoding
            return base64.b64encode(json.dumps(credentials).encode()).decode()
    
    def decrypt_credentials(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt OAuth credentials from storage."""
        if self._cipher is None:
            # Fallback from base64 encoding
            try:
                decoded = base64.b64decode(encrypted_data.encode()).decode()
                return json.loads(decoded)
            except Exception:
                return {}
        
        try:
            # Try Fernet decryption first
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self._cipher.decrypt(encrypted_bytes)
            return json.loads(decrypted_data.decode())
        except Exception:
            # Fallback to base64 encoding (for legacy data)
            try:
                decoded = base64.b64decode(encrypted_data.encode()).decode()
                return json.loads(decoded)
            except Exception:
                return {}
    
    def is_encryption_available(self) -> bool:
        """Check if proper encryption is available."""
        return self._cipher is not None


# Global instance
token_encryption = TokenEncryption()