"""Authentication primitives, standard library only.

Two deliberate choices, both from the "security is a property of the
architecture" rule:

- The password is never compared in plaintext and never stored. It is salted
  and stretched with PBKDF2-HMAC-SHA256, and verification is constant-time.
- The session token is a compact HS256 JWT signed with the same vault key that
  seals the ledger. It is built from ``hmac`` and ``base64url`` here rather than
  pulled from a library, so the token path carries no third-party code and the
  signature check is constant-time.

This is a demo-grade identity layer on purpose: one operator account, no
refresh tokens, no revocation list. The README's scope section says so out loud
rather than letting a reader assume more than is here.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import cast


class AuthError(Exception):
    """Raised when a credential or a token fails to verify."""


def hmac_safe_equals(left: str, right: str) -> bool:
    """Constant-time string comparison (does not leak length via early exit)."""
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


# -- password hashing ---------------------------------------------------------
_PBKDF2_ROUNDS = 240_000


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """Return a ``pbkdf2$rounds$salt$hash`` string for ``password``."""
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2${_PBKDF2_ROUNDS}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time verify of ``password`` against a stored hash."""
    try:
        scheme, rounds_s, salt_s, hash_s = encoded.split("$")
        if scheme != "pbkdf2":
            return False
        rounds = int(rounds_s)
        salt = _b64d(salt_s)
        expected = _b64d(hash_s)
    except (ValueError, KeyError):
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    return hmac.compare_digest(candidate, expected)


# -- compact HS256 JWT --------------------------------------------------------
def issue_token(subject: str, key: str, ttl: int) -> str:
    """Mint an HS256 JWT for ``subject`` valid for ``ttl`` seconds."""
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": subject, "iat": now, "exp": now + ttl, "iss": "shomer-gate"}
    segments = [_b64(json.dumps(header, separators=(",", ":")).encode()),
                _b64(json.dumps(payload, separators=(",", ":")).encode())]
    signing_input = ".".join(segments).encode("ascii")
    signature = hmac.new(key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    segments.append(_b64(signature))
    return ".".join(segments)


def verify_token(token: str, key: str) -> dict[str, object]:
    """Verify signature and expiry; return the claims or raise :class:`AuthError`."""
    try:
        header_s, payload_s, sig_s = token.split(".")
    except ValueError as exc:
        raise AuthError("malformed token") from exc

    signing_input = f"{header_s}.{payload_s}".encode("ascii")
    expected = hmac.new(key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, _b64d(sig_s)):
        raise AuthError("bad signature")

    claims = json.loads(_b64d(payload_s))
    if int(claims.get("exp", 0)) < int(time.time()):
        raise AuthError("token expired")
    return cast("dict[str, object]", claims)


# -- base64url helpers --------------------------------------------------------
def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)
