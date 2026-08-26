from unittest.mock import AsyncMock, Mock, call

import pytest

import app.core.token_store as token_store
from app.core.token_store import (
    delete_all_refresh_tokens,
    delete_refresh_token,
    get_refresh_token,
    save_refresh_token,
)


@pytest.mark.asyncio
async def test_get_refresh_token_when_redis_returns_none(monkeypatch):
    user_id = 123
    session_id = "session-1"
    mock_redis = AsyncMock()
    monkeypatch.setattr(token_store, "redis_client", mock_redis)
    mock_redis.get.return_value = None
    result = await get_refresh_token(user_id, session_id)
    assert result is None


@pytest.mark.asyncio
async def test_get_refresh_token_when_redis_returns_bytes(monkeypatch):
    user_id = 123
    session_id = "session-1"
    mock_redis = AsyncMock()
    monkeypatch.setattr(token_store, "redis_client", mock_redis)
    mock_redis.get.return_value = b"refresh_token"
    result = await get_refresh_token(user_id, session_id)

    assert result == "refresh_token"


@pytest.mark.asyncio
async def test_get_refresh_token_when_redis_returns_string(monkeypatch):
    user_id = 123
    session_id = "session-1"
    mock_redis = AsyncMock()
    monkeypatch.setattr(token_store, "redis_client", mock_redis)
    mock_redis.get.return_value = "refresh_token"
    result = await get_refresh_token(user_id, session_id)

    assert result == "refresh_token"


@pytest.mark.asyncio
async def test_get_refresh_token_uses_expected_redis_key(monkeypatch):
    user_id = 123
    session_id = "session-1"
    mock_redis = AsyncMock()
    monkeypatch.setattr(token_store, "redis_client", mock_redis)
    mock_redis.get.return_value = "refresh_token"
    await get_refresh_token(user_id, session_id)
    expected_key = f"session:{user_id}:{session_id}"
    mock_redis.get.assert_awaited_once_with(expected_key)


@pytest.mark.asyncio
async def test_save_refresh_token_uses_expected_redis_parameters(monkeypatch):
    user_id = 123
    session_id = "session-1"
    token = "refresh-token"
    expire_seconds = 3600
    mock_redis = AsyncMock()
    monkeypatch.setattr(token_store, "redis_client", mock_redis)
    await save_refresh_token(user_id, session_id, token, expire_seconds)
    expected_key = f"session:{user_id}:{session_id}"
    mock_redis.set.assert_awaited_once_with(expected_key, token, ex=expire_seconds)


@pytest.mark.asyncio
async def test_delete_refresh_token_uses_expected_redis_key(monkeypatch):
    user_id = 123
    session_id = "session-1"
    mock_redis = AsyncMock()
    monkeypatch.setattr(token_store, "redis_client", mock_redis)
    await delete_refresh_token(user_id, session_id)
    expected_key = f"session:{user_id}:{session_id}"
    mock_redis.delete.assert_awaited_once_with(expected_key)


@pytest.mark.asyncio
async def test_delete_all_refresh_tokens_scans_with_expected_pattern(monkeypatch):
    user_id = 123
    mock_redis = AsyncMock()
    monkeypatch.setattr(token_store, "redis_client", mock_redis)

    async def fake_scan(match):
        yield "session:123:a"
        yield "session:123:b"

    scan_mock = Mock(side_effect=fake_scan)
    mock_redis.scan_iter = scan_mock

    await delete_all_refresh_tokens(user_id)
    expected_pattern = f"session:{user_id}:*"
    mock_redis.scan_iter.assert_called_once_with(match=expected_pattern)


@pytest.mark.asyncio
async def test_delete_all_refresh_tokens_deletes_all_scanned_keys(monkeypatch):
    user_id = 123
    mock_redis = AsyncMock()
    monkeypatch.setattr(token_store, "redis_client", mock_redis)

    async def fake_scan(match):
        yield "session:123:a"
        yield "session:123:b"

    scan_mock = Mock(side_effect=fake_scan)
    mock_redis.scan_iter = scan_mock

    await delete_all_refresh_tokens(user_id)

    assert mock_redis.delete.await_args_list == [
        call("session:123:a"),
        call("session:123:b"),
    ]
