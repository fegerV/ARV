import json

import pytest

from app.utils import token_encryption as mod


def test_token_encryption_roundtrip_and_availability():
    encryptor = mod.TokenEncryption()
    credentials = {"access_token": "abc", "refresh_token": "xyz", "expires_in": 3600}

    encrypted = encryptor.encrypt_credentials(credentials)
    assert isinstance(encrypted, str)
    assert encrypted != json.dumps(credentials)
    assert encryptor.decrypt_credentials(encrypted) == credentials
    assert encryptor.is_encryption_available() is True


def test_token_encryption_fails_closed_without_cipher():
    """A missing cipher must fail loudly, never silently store plaintext.

    The plaintext (base64-of-JSON) fallback was removed deliberately: it
    turned a key/KDF problem into a silent security downgrade where OAuth
    tokens were persisted unencrypted.
    """
    encryptor = mod.TokenEncryption()
    encryptor._cipher = None

    credentials = {"token": "plain", "scope": ["disk", "info"]}

    assert encryptor.is_encryption_available() is False
    with pytest.raises(RuntimeError, match="not initialized"):
        encryptor.encrypt_credentials(credentials)
    with pytest.raises(RuntimeError, match="not initialized"):
        encryptor.decrypt_credentials("anything")


def test_token_encryption_propagates_cipher_errors():
    encryptor = mod.TokenEncryption()

    class BrokenCipher:
        def encrypt(self, _value):
            raise RuntimeError("encrypt failed")

        def decrypt(self, _value):
            raise RuntimeError("decrypt failed")

    encryptor._cipher = BrokenCipher()

    with pytest.raises(RuntimeError, match="encrypt failed"):
        encryptor.encrypt_credentials({"token": "fallback"})
    with pytest.raises(RuntimeError, match="decrypt failed"):
        encryptor.decrypt_credentials("Zm9v")


def test_token_encryption_init_cipher_failure(monkeypatch):
    monkeypatch.setattr(mod, "PBKDF2HMAC", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("kdf failed")))

    with pytest.raises(RuntimeError, match="kdf failed"):
        mod.TokenEncryption()
