import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import get_settings
from app.core.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def _token(payload_overrides: dict, key: str | None = None) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid.uuid4()),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=15),
        **payload_overrides,
    }
    return jwt.encode(payload, key or settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def test_hash_is_argon2id_and_salted():
    first = hash_password("correct horse")
    second = hash_password("correct horse")
    assert first.startswith("$argon2id$")
    assert first != second  # random salt per hash


def test_verify_password():
    stored = hash_password("correct horse")
    assert verify_password("correct horse", stored) is True
    assert verify_password("wrong password", stored) is False
    assert verify_password("anything", "not-a-real-hash") is False


def test_token_round_trip():
    user_id = uuid.uuid4()
    assert decode_access_token(create_access_token(user_id)) == user_id


def test_expired_token_rejected():
    past = datetime.now(timezone.utc) - timedelta(minutes=30)
    token = _token({"iat": past, "exp": past + timedelta(minutes=15)})
    with pytest.raises(TokenError):
        decode_access_token(token)


def test_token_signed_with_other_key_rejected():
    token = _token({}, key="x" * 40)
    with pytest.raises(TokenError):
        decode_access_token(token)


def test_wrong_token_type_rejected():
    token = _token({"type": "refresh"})
    with pytest.raises(TokenError):
        decode_access_token(token)