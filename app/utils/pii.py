"""Helpers for keeping personally identifiable information out of logs.

Logs are frequently shipped to third-party aggregators and retained far longer
than the primary database. Raw e-mail addresses and identifiers should not be
written to them; a stable, non-reversible-enough masked form is sufficient for
correlating events while limiting the privacy blast radius.
"""

from __future__ import annotations


def mask_email(email: str | None) -> str | None:
    """Mask an e-mail address for logging.

    ``alice.smith@example.com`` -> ``a***h@example.com``

    The domain is preserved (useful for diagnosing delivery/typo issues) while
    the local part is reduced to its first and last character. Returns ``None``
    for falsy input.
    """
    if not email or not isinstance(email, str):
        return None
    email = email.strip()
    if "@" not in email:
        return mask_token(email)
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        masked_local = local[0] + "*" * max(len(local) - 1, 0)
    else:
        masked_local = f"{local[0]}***{local[-1]}"
    return f"{masked_local}@{domain}"


def mask_token(value: str | None, keep: int = 4) -> str | None:
    """Reduce a token/identifier to a short, non-usable fingerprint."""
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    if len(value) <= keep:
        return "*" * len(value)
    return f"{value[:keep]}…{value[-2:]}"
