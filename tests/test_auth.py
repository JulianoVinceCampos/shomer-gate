"""Tests for the standard-library authentication primitives."""

from __future__ import annotations

import time

import pytest

from shomer_gate.api import auth

KEY = "unit-test-signing-key"


def test_password_hash_round_trip() -> None:
    encoded = auth.hash_password("emet-2026")
    assert encoded.startswith("pbkdf2$")
    assert auth.verify_password("emet-2026", encoded)
    assert not auth.verify_password("wrong", encoded)


def test_password_hash_is_salted() -> None:
    a = auth.hash_password("same")
    b = auth.hash_password("same")
    assert a != b  # distinct salts
    assert auth.verify_password("same", a)
    assert auth.verify_password("same", b)


def test_verify_password_rejects_garbage() -> None:
    assert not auth.verify_password("x", "not-a-valid-hash")
    assert not auth.verify_password("x", "bcrypt$1$salt$hash")


def test_token_round_trip() -> None:
    token = auth.issue_token("shomer", KEY, ttl=60)
    claims = auth.verify_token(token, KEY)
    assert claims["sub"] == "shomer"
    assert claims["iss"] == "shomer-gate"


def test_expired_token_rejected() -> None:
    token = auth.issue_token("shomer", KEY, ttl=-1)
    time.sleep(0.01)
    with pytest.raises(auth.AuthError, match="expired"):
        auth.verify_token(token, KEY)


def test_tampered_payload_rejected() -> None:
    token = auth.issue_token("shomer", KEY, ttl=60)
    header, _payload, sig = token.split(".")
    forged = f"{header}.{auth._b64(b'{\"sub\":\"root\",\"exp\":9999999999}')}.{sig}"
    with pytest.raises(auth.AuthError, match="signature"):
        auth.verify_token(forged, KEY)


def test_wrong_key_rejected() -> None:
    token = auth.issue_token("shomer", KEY, ttl=60)
    with pytest.raises(auth.AuthError):
        auth.verify_token(token, "a-different-key")


def test_malformed_token_rejected() -> None:
    with pytest.raises(auth.AuthError, match="malformed"):
        auth.verify_token("not-a-jwt", KEY)


def test_constant_time_equals() -> None:
    assert auth.hmac_safe_equals("shomer", "shomer")
    assert not auth.hmac_safe_equals("shomer", "someone")
