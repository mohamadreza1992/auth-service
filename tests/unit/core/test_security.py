from datetime import UTC, datetime, timedelta

import pytest
from jose.exceptions import JWTError

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)


def test_hash_password_does_not_return_plain_password():
    password = "secret123"
    hashed = hash_password(password)
    assert hashed != password


def test_hash_password_returns_string():
    password = "secret123"
    hashed = hash_password(password)

    assert isinstance(hashed, str)


def test_hash_password_generates_different_hash_for_same_password():
    password = "secret123"
    hashed_1 = hash_password(password)
    hashed_2 = hash_password(password)

    assert hashed_1 != hashed_2


def test_verify_password_with_correct_password():
    password = "secret123"
    hashed_password = hash_password(password)

    result = verify_password(password, hashed_password)

    assert result is True


def test_verify_password_with_wrong_password():
    password = "secret123"
    hashed_password = hash_password(password)

    result = verify_password("wrong_password", hashed_password)

    assert result is False


def test_create_access_token():
    data = {"sub": "123"}

    token = create_access_token(data)
    payload = decode_access_token(token)

    assert payload["sub"] == "123"
    assert payload["type"] == "access"
    assert "jti" in payload
    assert "exp" in payload


def test_create_access_token_with_custom_expiration():
    data = {"sub": "123"}

    token = create_access_token(data, expires_delta=timedelta(minutes=5))
    payload = decode_access_token(token)

    assert payload["sub"] == "123"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_decode_access_token_with_invalid_token():
    token = "123abc"
    with pytest.raises(JWTError):
        decode_access_token(token)


def test_decode_access_token_with_invalid_signature():
    data = {"sub": "123"}
    token = create_access_token(data)
    parts = token.split(".")
    parts[2] = "abcvcdfd"
    modified_token = ".".join(parts)
    with pytest.raises(JWTError):
        decode_access_token(modified_token)


def test_create_and_decode_refresh_token():
    data = {"sub": "abc"}

    refresh_token = create_refresh_token(data, jti="test-jti")
    payload = decode_refresh_token(refresh_token)

    assert payload["sub"] == "abc"
    assert payload["type"] == "refresh"
    assert payload["jti"] == "test-jti"


def test_create_refresh_token_with_custom_expiration():
    data = {"sub": "123"}
    now = datetime.now(UTC)

    refresh_token = create_refresh_token(
        data, jti="test-jti", expires_delta=timedelta(days=7)
    )
    payload = decode_refresh_token(refresh_token)
    actual_exp = datetime.fromtimestamp(payload["exp"], UTC)
    expected_exp = now + timedelta(days=7)

    assert payload["sub"] == "123"
    assert payload["type"] == "refresh"
    assert payload["jti"] == "test-jti"
    difference = abs(actual_exp - expected_exp)
    assert difference < timedelta(seconds=5)


def test_decode_refresh_token_with_access_token():
    data = {"sub": "123"}
    token = create_access_token(data)
    with pytest.raises(JWTError):
        decode_refresh_token(token)
