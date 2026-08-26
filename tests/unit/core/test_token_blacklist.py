from unittest.mock import AsyncMock

import pytest

import app.core.token_blacklist as token_blacklist
from app.core.token_blacklist import blacklist_token, is_token_blacklisted


@pytest.mark.asyncio
async def test_is_token_blacklisted_when_exists(monkeypatch):
    jti = "abc"
    mock_redis = AsyncMock()
    monkeypatch.setattr(token_blacklist, "redis_client", mock_redis)
    mock_redis.exists.return_value = 1
    result = await is_token_blacklisted(jti)

    assert result is True


@pytest.mark.asyncio
async def test_is_token_blacklisted_uses_expected_key(monkeypatch):
    jti = "abc"
    mock_redis = AsyncMock()
    monkeypatch.setattr(token_blacklist, "redis_client", mock_redis)
    await is_token_blacklisted(jti)
    expected_key = f"blacklist:{jti}"
    mock_redis.exists.assert_awaited_once_with(expected_key)


@pytest.mark.asyncio
async def test_is_token_blacklisted_when_not_exists(monkeypatch):
    jti = "abc"
    mock_redis = AsyncMock()
    monkeypatch.setattr(token_blacklist, "redis_client", mock_redis)
    mock_redis.exists.return_value = 0
    result = await is_token_blacklisted(jti)

    assert result is False


@pytest.mark.asyncio
async def test_blacklist_token_uses_expected_redis_parameters(monkeypatch):
    jti = "abc"
    expire_seconds = 3600
    mock_redis = AsyncMock()
    monkeypatch.setattr(token_blacklist, "redis_client", mock_redis)
    await blacklist_token(jti, expire_seconds)
    expected_key = f"blacklist:{jti}"
    mock_redis.set.assert_awaited_once_with(expected_key, "true", ex=expire_seconds)
