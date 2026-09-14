"""Regression tests for the security remediation.

These tests pin the *secure* behaviour that was introduced while fixing the
findings in ``SECURITY_AUDIT_REPORT.md``. If any of them regresses, the
corresponding vulnerability is back.
"""

from __future__ import annotations

import hashlib
import time

import pytest

from app.utils.pii import mask_email, mask_token


# ---------------------------------------------------------------------------
# ARV-029 — PII masking
# ---------------------------------------------------------------------------

class TestMaskEmail:
    def test_masks_local_part_and_keeps_domain(self):
        assert mask_email("alice.smith@example.com") == "a***h@example.com"

    def test_short_local_part(self):
        assert mask_email("ab@example.com") == "a*@example.com"
        assert mask_email("a@example.com") == "a@example.com"

    def test_none_and_empty(self):
        assert mask_email(None) is None
        assert mask_email("") is None

    def test_non_email_value_is_fingerprinted(self):
        masked = mask_email("not-an-email-but-long-token")
        assert masked is not None
        assert "not-an-email-but-long-token" != masked

    def test_mask_token(self):
        assert mask_token("abcdefghij") == "abcd…ij"
        assert mask_token("abc") == "***"
        assert mask_token(None) is None


# ---------------------------------------------------------------------------
# ARV-004 — HMAC-signed Yandex Disk proxy URLs
# ---------------------------------------------------------------------------

class TestSignedMediaUrls:
    def _parse(self, url: str) -> dict:
        from urllib.parse import parse_qs, urlparse

        return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}

    def test_round_trip_accepts_valid_signature(self):
        from app.utils.signed_urls import build_yd_file_url, verify_yd_file_signature

        url = build_yd_file_url("/content/photo.jpg", company_id=7)
        qs = self._parse(url)
        assert verify_yd_file_signature(
            qs["path"], int(qs["company_id"]), qs["exp"], qs["sig"]
        )

    def test_tampered_path_is_rejected(self):
        from app.utils.signed_urls import build_yd_file_url, verify_yd_file_signature

        url = build_yd_file_url("/content/photo.jpg", company_id=7)
        qs = self._parse(url)
        assert not verify_yd_file_signature(
            "/content/secret.jpg", int(qs["company_id"]), qs["exp"], qs["sig"]
        )

    def test_tampered_company_is_rejected(self):
        from app.utils.signed_urls import build_yd_file_url, verify_yd_file_signature

        url = build_yd_file_url("/content/photo.jpg", company_id=7)
        qs = self._parse(url)
        assert not verify_yd_file_signature(qs["path"], 8, qs["exp"], qs["sig"])

    def test_expired_signature_is_rejected(self):
        from app.utils.signed_urls import _signature, verify_yd_file_signature

        exp = int(time.time()) - 10
        sig = _signature("/content/photo.jpg", 7, exp)
        assert not verify_yd_file_signature("/content/photo.jpg", 7, exp, sig)

    def test_missing_signature_is_rejected(self):
        from app.utils.signed_urls import verify_yd_file_signature

        assert not verify_yd_file_signature("/x.jpg", 1, int(time.time()) + 60, None)
        assert not verify_yd_file_signature("/x.jpg", 1, None, "deadbeef")


# ---------------------------------------------------------------------------
# ARV-015 — legacy unsalted SHA-256 hashes
# ---------------------------------------------------------------------------

class TestLegacyPasswordHashes:
    def test_legacy_hash_rejected_when_disabled(self, monkeypatch):
        from app.core import security

        monkeypatch.setattr(
            security.settings, "ALLOW_LEGACY_PASSWORD_HASHES", False, raising=False
        )
        monkeypatch.setattr(security.settings, "ENVIRONMENT", "development", raising=False)
        legacy = hashlib.sha256(b"hunter2").hexdigest()
        assert security.is_legacy_password_hash(legacy)
        assert security.verify_password("hunter2", legacy) is False

    def test_legacy_hash_accepted_when_explicitly_enabled(self, monkeypatch):
        from app.core import security

        monkeypatch.setattr(
            security.settings, "ALLOW_LEGACY_PASSWORD_HASHES", True, raising=False
        )
        monkeypatch.setattr(security.settings, "ENVIRONMENT", "development", raising=False)
        legacy = hashlib.sha256(b"hunter2").hexdigest()
        assert security.verify_password("hunter2", legacy) is True
        assert security.verify_password("wrong", legacy) is False

    def test_legacy_hash_never_accepted_in_production(self, monkeypatch):
        from app.core import security

        monkeypatch.setattr(
            security.settings, "ALLOW_LEGACY_PASSWORD_HASHES", True, raising=False
        )
        monkeypatch.setattr(security.settings, "ENVIRONMENT", "production", raising=False)
        legacy = hashlib.sha256(b"hunter2").hexdigest()
        assert security.verify_password("hunter2", legacy) is False

    def test_modern_hash_still_works(self):
        from app.core import security

        hashed = security.get_password_hash("s3cret-password")
        assert security.verify_password("s3cret-password", hashed) is True
        assert security.verify_password("nope", hashed) is False

    def test_needs_rehash_for_legacy(self):
        from app.core import security

        legacy = hashlib.sha256(b"hunter2").hexdigest()
        assert security.needs_password_rehash(legacy) is True


# ---------------------------------------------------------------------------
# ARV-014 — input validation on the public analytics endpoints
# ---------------------------------------------------------------------------

class TestAnalyticsInputSanitising:
    def test_clean_str_truncates_and_strips(self):
        from app.api.routes.analytics import _clean_str

        assert _clean_str("  hello  ") == "hello"
        assert _clean_str("") is None
        assert _clean_str(None) is None
        assert _clean_str("x" * 5000, 512) == "x" * 512

    def test_clean_duration_bounds(self):
        from app.api.routes.analytics import _clean_duration

        assert _clean_duration(30) == 30
        assert _clean_duration("45") == 45
        assert _clean_duration(-1) is None
        assert _clean_duration("nope") is None
        assert _clean_duration(None) is None
        # Clamped to the 24h ceiling.
        assert _clean_duration(10 ** 12) == 60 * 60 * 24


# ---------------------------------------------------------------------------
# ARV-023 — WebSocket origin validation
# ---------------------------------------------------------------------------

class _FakeWS:
    def __init__(self, headers: dict):
        self.headers = headers


class TestWebSocketOrigin:
    def test_missing_origin_allowed_for_native_clients(self):
        from app.api.routes.alerts_ws import _is_allowed_origin

        assert _is_allowed_origin(_FakeWS({})) is True

    def test_same_host_origin_allowed(self):
        from app.api.routes.alerts_ws import _is_allowed_origin

        ws = _FakeWS({"origin": "https://ar.example.com", "host": "ar.example.com"})
        assert _is_allowed_origin(ws) is True

    def test_foreign_origin_rejected(self):
        from app.api.routes.alerts_ws import _is_allowed_origin

        ws = _FakeWS({"origin": "https://evil.example.net", "host": "ar.example.com"})
        assert _is_allowed_origin(ws) is False


# ---------------------------------------------------------------------------
# ARV-006 / ARV-007 — mass-assignment allow-lists
# ---------------------------------------------------------------------------

class TestMassAssignmentAllowLists:
    def test_video_updatable_fields_exclude_sensitive_columns(self):
        from app.api.routes.videos import _LEGACY_VIDEO_UPDATABLE_FIELDS

        for forbidden in ("id", "company_id", "project_id", "ar_content_id", "unique_id"):
            assert forbidden not in _LEGACY_VIDEO_UPDATABLE_FIELDS

    def test_rotation_sanitise_drops_unknown_and_identity_keys(self):
        from app.api.routes.rotation import _sanitise_payload

        clean = _sanitise_payload(
            {
                "id": 999,
                "ar_content_id": 12345,
                "created_at": "2020-01-01",
                "rotation_type": "random",
            }
        )
        assert "id" not in clean
        assert "ar_content_id" not in clean
        assert "created_at" not in clean
        assert clean["rotation_type"] == "random"


# ---------------------------------------------------------------------------
# ARV-003 — fail-closed company scoping
# ---------------------------------------------------------------------------

class _FakeUser:
    def __init__(self, company_id, is_super_admin=False):
        self.id = 1
        self.company_id = company_id
        self.is_super_admin = is_super_admin
        self.is_active = True


class TestCompanyScoping:
    def test_user_without_company_is_denied(self):
        from app.api.deps_authz import user_can_access_company

        assert user_can_access_company(_FakeUser(None), 1) is False
        assert user_can_access_company(_FakeUser(None), None) is False

    def test_user_can_only_access_own_company(self):
        from app.api.deps_authz import user_can_access_company

        assert user_can_access_company(_FakeUser(5), 5) is True
        assert user_can_access_company(_FakeUser(5), 6) is False

    def test_super_admin_can_access_any_company(self):
        from app.api.deps_authz import user_can_access_company

        assert user_can_access_company(_FakeUser(None, is_super_admin=True), 42) is True

    def test_ensure_authenticated_user_rejects_non_user(self):
        from fastapi import HTTPException

        from app.api.deps_authz import ensure_authenticated_user

        # A dependency-object placeholder (what a bypassed Depends() default
        # looks like) must never be treated as an authenticated principal.
        with pytest.raises(HTTPException) as exc:
            ensure_authenticated_user(object())
        assert exc.value.status_code == 403

    def test_ensure_authenticated_user_accepts_real_user(self):
        from app.api.deps_authz import ensure_authenticated_user
        from app.models.user import User

        user = User(email="u@example.com", hashed_password="x", is_active=True)
        assert ensure_authenticated_user(user) is user
