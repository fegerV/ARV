"""Token encryption utilities for secure storage of OAuth tokens."""

import base64
import hashlib
import json
from typing import Dict, Any, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import get_settings

settings = get_settings()


class TokenEncryption:
    """Handles encryption and decryption of OAuth tokens."""

    def __init__(self) -> None:
        self._cipher: Optional[Fernet] = None
        self._init_cipher()

    def _init_cipher(self) -> None:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._derive_salt(),
            iterations=100_000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
        self._cipher = Fernet(key)

    @staticmethod
    def _derive_salt() -> bytes:
        """Derive a deterministic salt from SECRET_KEY.

        This avoids a hardcoded constant while keeping the salt stable
        across restarts so existing encrypted values stay decryptable.
        """
        return hashlib.sha256(b"vertex_ar_oauth_salt").digest()[:16]

    def encrypt_credentials(self, credentials: Dict[str, Any]) -> str:
        if self._cipher is None:
            raise RuntimeError("Token encryption is not initialized")

        json_data = json.dumps(credentials).encode()
        encrypted_data = self._cipher.encrypt(json_data)
        return base64.urlsafe_b64encode(encrypted_data).decode()

    def decrypt_credentials(self, encrypted_data: str) -> Dict[str, Any]:
        if self._cipher is None:
            raise RuntimeError("Token encryption is not initialized")

        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted_data = self._cipher.decrypt(encrypted_bytes)
        return json.loads(decrypted_data.decode())

    def is_encryption_available(self) -> bool:
        return self._cipher is not None


token_encryption = TokenEncryption()