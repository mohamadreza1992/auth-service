from datetime import UTC, datetime
from ipaddress import IPv4Address
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

import app.features.sessions.service as service
from app.features.sessions.entities import Session


def make_session() -> Session:
    now = datetime.now(UTC)

    return Session(
        session_id=uuid4(),
        user_id=123,
        jti="test-jti",
        device="Chrome",
        ip_address=IPv4Address("127.0.0.1"),
        created_at=now,
        last_used_at=now,
    )


@pytest.mark.asyncio
async def test_create_session(monkeypatch):
    save_mock = AsyncMock()
    monkeypatch.setattr(service, "save_session", save_mock)

    result = await service.create_session(
        user_id=123,
        jti="test-jti",
        device="Chrome",
        ip_address=IPv4Address("127.0.0.1"),
        expire_seconds=3600,
    )

    assert isinstance(result, Session)
    assert result.user_id == 123
    assert result.jti == "test-jti"
    assert result.device == "Chrome"
    assert str(result.ip_address) == "127.0.0.1"
    assert result.created_at == result.last_used_at

    save_mock.assert_awaited_once()
    assert save_mock.await_args is not None

    args = save_mock.await_args.args

    saved_session = args[0]
    expire_seconds = args[1]

    assert isinstance(saved_session, Session)
    assert saved_session.user_id == 123
    assert saved_session.jti == "test-jti"
    assert saved_session.device == "Chrome"
    assert str(saved_session.ip_address) == "127.0.0.1"
    assert expire_seconds == 3600


@pytest.mark.asyncio
async def test_get_validated_session(monkeypatch):
    session = make_session()
    validate_mock = AsyncMock(return_value=session)

    monkeypatch.setattr(
        service,
        "validate_session",
        validate_mock,
    )

    result = await service.get_validated_session(
        session.user_id,
        str(session.session_id),
    )

    assert result is session

    validate_mock.assert_awaited_once_with(
        session.user_id,
        str(session.session_id),
    )


@pytest.mark.asyncio
async def test_revoke_session(monkeypatch):
    delete_mock = AsyncMock()

    monkeypatch.setattr(
        service,
        "delete_session",
        delete_mock,
    )

    await service.revoke_session(
        123,
        "session-1",
    )

    delete_mock.assert_awaited_once_with(
        123,
        "session-1",
    )


@pytest.mark.asyncio
async def test_revoke_all_sessions(monkeypatch):
    delete_all_mock = AsyncMock()
    acquire_mock = AsyncMock(return_value="lock-token")
    release_mock = AsyncMock(return_value=True)

    monkeypatch.setattr(
        service,
        "delete_all_sessions",
        delete_all_mock,
    )

    monkeypatch.setattr(
        service,
        "acquire_session_lock",
        acquire_mock,
    )

    monkeypatch.setattr(
        service,
        "release_session_lock",
        release_mock,
    )

    await service.revoke_all_sessions(123)

    acquire_mock.assert_awaited_once_with(123)

    delete_all_mock.assert_awaited_once_with(123)

    release_mock.assert_awaited_once_with(
        123,
        "lock-token",
    )


@pytest.mark.asyncio
async def test_refresh_session_activity(monkeypatch):
    touch_mock = AsyncMock()

    monkeypatch.setattr(
        service,
        "touch_session",
        touch_mock,
    )

    await service.refresh_session_activity(
        123,
        "session-1",
    )

    touch_mock.assert_awaited_once_with(
        123,
        "session-1",
    )


@pytest.mark.asyncio
async def test_rotate_session_jti(monkeypatch):
    update_mock = AsyncMock(return_value=True)

    monkeypatch.setattr(
        service,
        "update_session_jti",
        update_mock,
    )

    result = await service.rotate_session_jti(
        123,
        "session-1",
        "old-jti",
        "new-jti",
    )

    assert result is True

    update_mock.assert_awaited_once_with(
        123,
        "session-1",
        "old-jti",
        "new-jti",
    )


@pytest.mark.asyncio
async def test_list_user_sessions(monkeypatch):
    session_1 = make_session()
    session_2 = make_session()

    get_all_mock = AsyncMock(
        return_value=[
            session_1,
            session_2,
        ]
    )

    monkeypatch.setattr(
        service,
        "get_all_sessions",
        get_all_mock,
    )

    result = await service.list_user_sessions(123)

    assert result == [session_1, session_2]

    get_all_mock.assert_awaited_once_with(123)


@pytest.mark.asyncio
async def test_list_user_sessions_when_empty(monkeypatch):
    get_all_mock = AsyncMock(return_value=[])

    monkeypatch.setattr(
        service,
        "get_all_sessions",
        get_all_mock,
    )

    result = await service.list_user_sessions(123)

    assert result == []

    get_all_mock.assert_awaited_once_with(123)
