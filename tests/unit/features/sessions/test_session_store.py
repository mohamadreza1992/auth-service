from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, call
from uuid import uuid4

import pytest
from redis.exceptions import WatchError

import app.features.sessions.session_store as session_store
from app.features.sessions.schemas import Session
from app.features.sessions.session_store import (
    delete_all_sessions,
    delete_session,
    get_all_sessions,
    get_session,
    save_session,
    touch_session,
    update_session_jti,
)


def make_session(
    user_id: int = 123,
    session_id=None,
    jti: str = "test-jti",
) -> Session:
    now = datetime.now(UTC)

    return Session(
        session_id=session_id or uuid4(),
        user_id=user_id,
        jti=jti,
        created_at=now,
        last_used_at=now,
    )


@pytest.mark.asyncio
async def test_get_session_when_redis_returns_none(monkeypatch):
    mock_redis = AsyncMock()
    monkeypatch.setattr(session_store, "redis_client", mock_redis)

    mock_redis.get.return_value = None

    result = await get_session(123, "session-1")

    assert result is None


@pytest.mark.asyncio
async def test_get_session_returns_session(monkeypatch):
    mock_redis = AsyncMock()
    monkeypatch.setattr(session_store, "redis_client", mock_redis)

    session = make_session()

    mock_redis.get.return_value = session.model_dump_json()

    result = await get_session(123, str(session.session_id))

    assert isinstance(result, Session)
    assert result.session_id == session.session_id
    assert result.user_id == session.user_id
    assert result.jti == session.jti


@pytest.mark.asyncio
async def test_get_session_uses_expected_redis_key(monkeypatch):
    mock_redis = AsyncMock()
    monkeypatch.setattr(session_store, "redis_client", mock_redis)

    mock_redis.get.return_value = None

    await get_session(123, "session-1")

    mock_redis.get.assert_awaited_once_with("session:123:session-1")


@pytest.mark.asyncio
async def test_save_session_uses_expected_redis_parameters(monkeypatch):
    mock_redis = AsyncMock()
    monkeypatch.setattr(session_store, "redis_client", mock_redis)

    session = make_session()
    expire_seconds = 3600

    await save_session(session, expire_seconds)

    expected_key = f"session:{session.user_id}:{session.session_id}"

    mock_redis.set.assert_awaited_once_with(
        expected_key,
        session.model_dump_json(),
        ex=expire_seconds,
    )


@pytest.mark.asyncio
async def test_delete_session_uses_expected_redis_key(monkeypatch):
    mock_redis = AsyncMock()
    monkeypatch.setattr(session_store, "redis_client", mock_redis)

    await delete_session(123, "session-1")

    mock_redis.delete.assert_awaited_once_with(
        "session:123:session-1",
    )


@pytest.mark.asyncio
async def test_delete_all_sessions_scans_expected_pattern(monkeypatch):
    mock_redis = AsyncMock()
    monkeypatch.setattr(session_store, "redis_client", mock_redis)

    async def fake_scan(match):
        yield "session:123:a"
        yield "session:123:b"

    scan_mock = Mock(side_effect=fake_scan)
    mock_redis.scan_iter = scan_mock

    await delete_all_sessions(123)

    scan_mock.assert_called_once_with(
        match="session:123:*",
    )


@pytest.mark.asyncio
async def test_delete_all_sessions_deletes_all_sessions(monkeypatch):
    mock_redis = AsyncMock()
    monkeypatch.setattr(session_store, "redis_client", mock_redis)

    async def fake_scan(match):
        yield "session:123:a"
        yield "session:123:b"

    mock_redis.scan_iter = Mock(side_effect=fake_scan)

    await delete_all_sessions(123)

    assert mock_redis.delete.await_args_list == [
        call("session:123:a"),
        call("session:123:b"),
    ]


@pytest.mark.asyncio
async def test_touch_session_does_nothing_when_session_not_found(monkeypatch):
    mock_redis = Mock()
    mock_pipeline = Mock()

    monkeypatch.setattr(session_store, "redis_client", mock_redis)

    mock_redis.pipeline.return_value = mock_pipeline

    mock_pipeline.__aenter__ = AsyncMock(return_value=mock_pipeline)
    mock_pipeline.__aexit__ = AsyncMock(return_value=None)

    mock_pipeline.watch = AsyncMock()
    mock_pipeline.get = AsyncMock(return_value=None)
    mock_pipeline.unwatch = AsyncMock()

    await touch_session(123, "session-1")

    mock_pipeline.watch.assert_awaited_once_with(
        "session:123:session-1",
    )

    mock_pipeline.get.assert_awaited_once_with(
        "session:123:session-1",
    )

    mock_pipeline.unwatch.assert_awaited_once()

    mock_pipeline.set.assert_not_called()


@pytest.mark.asyncio
async def test_touch_session_updates_last_used_at(monkeypatch):
    mock_redis = Mock()
    mock_pipeline = Mock()

    monkeypatch.setattr(session_store, "redis_client", mock_redis)

    mock_redis.pipeline.return_value = mock_pipeline

    mock_pipeline.__aenter__ = AsyncMock(return_value=mock_pipeline)
    mock_pipeline.__aexit__ = AsyncMock(return_value=None)

    mock_pipeline.watch = AsyncMock()
    mock_pipeline.get = AsyncMock()
    mock_pipeline.execute = AsyncMock(return_value=[True])

    session = make_session()
    old_last_used_at = session.last_used_at

    mock_pipeline.get.return_value = session.model_dump_json()

    await touch_session(
        123,
        str(session.session_id),
    )

    mock_pipeline.multi.assert_called_once()

    mock_pipeline.set.assert_called_once()

    args, kwargs = mock_pipeline.set.call_args

    data = args[1]

    updated_session = Session.model_validate_json(data)

    assert updated_session.last_used_at > old_last_used_at
    assert kwargs == {"keepttl": True}

    mock_pipeline.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_session_jti_does_nothing_when_session_not_found(monkeypatch):
    mock_redis = Mock()
    mock_pipeline = Mock()

    monkeypatch.setattr(session_store, "redis_client", mock_redis)

    mock_redis.pipeline.return_value = mock_pipeline

    mock_pipeline.__aenter__ = AsyncMock(return_value=mock_pipeline)
    mock_pipeline.__aexit__ = AsyncMock(return_value=None)

    mock_pipeline.watch = AsyncMock()
    mock_pipeline.get = AsyncMock(return_value=None)
    mock_pipeline.unwatch = AsyncMock()

    result = await update_session_jti(
        123,
        "session-1",
        "old-jti",
        "new-jti",
    )

    assert result is False
    mock_pipeline.watch.assert_awaited_once_with(
        "session:123:session-1",
    )
    mock_pipeline.get.assert_awaited_once_with(
        "session:123:session-1",
    )
    mock_pipeline.unwatch.assert_awaited_once()
    mock_pipeline.set.assert_not_called()


@pytest.mark.asyncio
async def test_update_session_jti_updates_jti(monkeypatch):
    mock_redis = Mock()
    mock_pipeline = Mock()

    monkeypatch.setattr(session_store, "redis_client", mock_redis)

    mock_redis.pipeline.return_value = mock_pipeline

    mock_pipeline.__aenter__ = AsyncMock(return_value=mock_pipeline)
    mock_pipeline.__aexit__ = AsyncMock(return_value=None)

    mock_pipeline.watch = AsyncMock()
    mock_pipeline.get = AsyncMock()
    mock_pipeline.unwatch = AsyncMock()
    mock_pipeline.execute = AsyncMock(return_value=[True])

    session = make_session(jti="old-jti")

    mock_pipeline.get.return_value = session.model_dump_json()

    result = await update_session_jti(
        123,
        str(session.session_id),
        "old-jti",
        "new-jti",
    )

    assert result is True

    mock_pipeline.multi.assert_called_once()

    mock_pipeline.set.assert_called_once()

    args, kwargs = mock_pipeline.set.call_args
    data = args[1]

    updated_session = Session.model_validate_json(data)

    assert updated_session.jti == "new-jti"
    assert kwargs == {"keepttl": True}

    mock_pipeline.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_all_sessions_returns_sessions(monkeypatch):
    mock_redis = AsyncMock()
    monkeypatch.setattr(session_store, "redis_client", mock_redis)

    session_1 = make_session(session_id=uuid4())
    session_2 = make_session(session_id=uuid4())

    async def fake_scan(match):
        yield f"session:123:{session_1.session_id}"
        yield f"session:123:{session_2.session_id}"

    mock_redis.scan_iter = Mock(side_effect=fake_scan)

    mock_redis.get.side_effect = [
        session_1.model_dump_json(),
        session_2.model_dump_json(),
    ]

    result = await get_all_sessions(123)

    assert len(result) == 2
    assert result[0].session_id == session_1.session_id
    assert result[1].session_id == session_2.session_id


@pytest.mark.asyncio
async def test_get_all_sessions_skips_deleted_session(monkeypatch):
    mock_redis = AsyncMock()
    monkeypatch.setattr(session_store, "redis_client", mock_redis)

    session = make_session()

    async def fake_scan(match):
        yield f"session:123:{session.session_id}"
        yield "session:123:deleted"

    mock_redis.scan_iter = Mock(side_effect=fake_scan)

    mock_redis.get.side_effect = [
        session.model_dump_json(),
        None,
    ]

    result = await get_all_sessions(123)

    assert len(result) == 1
    assert result[0].session_id == session.session_id


@pytest.mark.asyncio
async def test_update_session_jti_returns_false_on_watch_error(monkeypatch):
    mock_redis = Mock()
    mock_pipeline = Mock()

    monkeypatch.setattr(session_store, "redis_client", mock_redis)

    mock_redis.pipeline.return_value = mock_pipeline

    mock_pipeline.__aenter__ = AsyncMock(return_value=mock_pipeline)
    mock_pipeline.__aexit__ = AsyncMock(return_value=None)

    mock_pipeline.watch = AsyncMock()
    mock_pipeline.get = AsyncMock(
        return_value=make_session(jti="old-jti").model_dump_json()
    )
    mock_pipeline.execute = AsyncMock(side_effect=WatchError())

    result = await update_session_jti(
        123,
        "session-1",
        "old-jti",
        "new-jti",
    )

    assert result is False

    mock_pipeline.watch.assert_awaited_once_with(
        "session:123:session-1",
    )

    mock_pipeline.execute.assert_awaited_once()
