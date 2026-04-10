import base64
import json

from app.utils import token_encryption as mod


def test_token_encryption_roundtrip_and_availability():
    encryptor = mod.TokenEncryption()
    credentials = {"access_token": "abc", "refresh_token": "xyz", "expires_in": 3600}

    encrypted = encryptor.encrypt_credentials(credentials)
    assert isinstance(encrypted, str)
    assert encrypted != json.dumps(credentials)
    assert encryptor.decrypt_credentials(encrypted) == credentials
    assert encryptor.is_encryption_available() is True


def test_token_encryption_cipherless_fallback(monkeypatch):
    encryptor = mod.TokenEncryption()
    encryptor._cipher = None

    credentials = {"token": "plain", "scope": ["disk", "info"]}
    encoded = encryptor.encrypt_credentials(credentials)
    assert base64.b64decode(encoded.encode()).decode() == json.dumps(credentials)
    assert encryptor.decrypt_credentials(encoded) == credentials
    assert encryptor.decrypt_credentials("not-valid-base64") == {}
    assert encryptor.is_encryption_available() is False


def test_token_encryption_encrypt_and_decrypt_fallback_paths(monkeypatch):
    encryptor = mod.TokenEncryption()
    credentials = {"token": "fallback"}

    class BrokenCipher:
        def encrypt(self, _value):
            raise RuntimeError("encrypt failed")

        def decrypt(self, _value):
            raise RuntimeError("decrypt failed")

    encryptor._cipher = BrokenCipher()
    encrypted = encryptor.encrypt_credentials(credentials)
    assert base64.b64decode(encrypted.encode()).decode() == json.dumps(credentials)
    assert encryptor.decrypt_credentials(encrypted) == credentials
    assert encryptor.decrypt_credentials("%%%") == {}


def test_token_encryption_init_cipher_failure(monkeypatch):
    monkeypatch.setattr(mod, "PBKDF2HMAC", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("kdf failed")))
    encryptor = mod.TokenEncryption()
    assert encryptor._cipher is None
