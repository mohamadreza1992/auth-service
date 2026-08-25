from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_refresh_token, hash_password
from app.core.token_blacklist import is_token_blacklisted
from app.core.token_store import get_refresh_token
from app.features.auth.models import User
from app.features.auth.schemas import RefreshTokenRequest, UserCreate, UserLogin
from app.features.auth.service import (
    create_refresh_token,
    login_user,
    logout_all_users,
    logout_user,
    refresh_access_token,
    register_user,
    save_refresh_token,
)


@pytest.mark.asyncio
async def test_success_register_user(db_session: AsyncSession):
    user_data = UserCreate(
        email="register@example.com",
        password="StrongPassword123",
    )

    created_user = await register_user(
        db_session,
        user_data,
    )
    assert created_user is not None
    assert created_user.email == user_data.email
    assert created_user.is_active is True
    assert created_user.password_hash != user_data.password


@pytest.mark.asyncio
async def test_register_user_with_existing_email(db_session: AsyncSession):
    existing_user = User(
        email="duplicate@example.com",
        password_hash="hashed_password",
        is_active=True,
    )

    db_session.add(existing_user)
    await db_session.commit()
    user_data = UserCreate(
        email="duplicate@example.com",
        password="StrongPassword123",
    )
    with pytest.raises(HTTPException) as exc_info:
        await register_user(db_session, user_data)

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_successful_login(
    db_session: AsyncSession,
):
    existing_user = User(
        email="login@example.com",
        password_hash=hash_password("StrongPassword123"),
        is_active=True,
    )

    db_session.add(existing_user)
    await db_session.commit()
    user_data = UserLogin(
        email="login@example.com",
        password="StrongPassword123",
    )
    result = await login_user(db_session, user_data)
    assert result.access_token
    assert result.refresh_token
    assert result.token_type == "bearer"
    payload = decode_refresh_token(result.refresh_token)

    stored_token = await get_refresh_token(
        int(payload["sub"]),
        payload["session_id"],
    )

    assert stored_token == result.refresh_token


@pytest.mark.asyncio
async def test_login_user_not_found(db_session: AsyncSession):
    user_data = UserLogin(
        email="not-found@example.com",
        password="StrongPassword123",
    )
    with pytest.raises(HTTPException) as exc_info:
        await login_user(db_session, user_data)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_user_wrong_password(db_session: AsyncSession):
    existing_user = User(
        email="login@example.com",
        password_hash=hash_password("StrongPassword123"),
        is_active=True,
    )

    db_session.add(existing_user)
    await db_session.commit()
    user_data = UserLogin(
        email="login@example.com",
        password="wrongpassword",
    )

    with pytest.raises(HTTPException) as exc_info:
        await login_user(db_session, user_data)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid credentials"


@pytest.mark.asyncio
async def test_refresh_access_token_without_user_id():
    refresh_token = create_refresh_token(
        data={
            "email": "test@example.com",
            "session_id": "test-session",
        }
    )

    data = RefreshTokenRequest(
        refresh_token=refresh_token,
    )
    with pytest.raises(HTTPException) as exc_info:
        await refresh_access_token(data)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid refresh token"


@pytest.mark.asyncio
async def test_refresh_access_token_without_session_id():
    refresh_token = create_refresh_token(
        data={
            "sub": "1",
            "email": "test@example.com",
        }
    )
    data = RefreshTokenRequest(
        refresh_token=refresh_token,
    )
    with pytest.raises(HTTPException) as exc_info:
        await refresh_access_token(data)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid refresh token"


@pytest.mark.asyncio
async def test_refresh_access_token_token_not_found(redis_client: Redis):
    refresh_token = create_refresh_token(
        data={
            "sub": "1",
            "email": "test@example.com",
            "session_id": "not-found-session-001",
        }
    )

    data = RefreshTokenRequest(
        refresh_token=refresh_token,
    )
    with pytest.raises(HTTPException) as exc_info:
        await refresh_access_token(data)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid refresh token"


@pytest.mark.asyncio
async def test_refresh_access_token_token_mismatch(redis_client: Redis):
    correct_token = create_refresh_token(
        data={
            "sub": "1",
            "email": "test@example.com",
            "session_id": "test-session",
        }
    )

    wrong_token = create_refresh_token(
        data={
            "sub": "1",
            "email": "test@example.com",
            "session_id": "test-session",
        },
        expires_delta=timedelta(days=2),
    )
    await save_refresh_token(
        user_id=1,
        session_id="test-session",
        token=correct_token,
        expire_seconds=60,
    )
    data = RefreshTokenRequest(
        refresh_token=wrong_token,
    )
    with pytest.raises(HTTPException) as exc_info:
        await refresh_access_token(data)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid refresh token"


@pytest.mark.asyncio
async def test_successful_refresh_access_token(redis_client: Redis):
    refresh_token = create_refresh_token(
        data={
            "sub": "1",
            "email": "test@example.com",
            "session_id": "test-session",
        }
    )
    await save_refresh_token(
        user_id=1,
        session_id="test-session",
        token=refresh_token,
        expire_seconds=60,
    )
    data = RefreshTokenRequest(
        refresh_token=refresh_token,
    )
    result = await refresh_access_token(data)
    assert result.access_token
    assert result.refresh_token
    assert result.refresh_token != refresh_token

    stored_token = await get_refresh_token(
        1,
        "test-session",
    )

    assert stored_token == result.refresh_token
    assert stored_token != refresh_token


@pytest.mark.asyncio
async def test_successful_logout_user(redis_client: Redis):
    refresh_token = create_refresh_token(
        data={
            "sub": "1",
            "email": "test@example.com",
            "session_id": "test-session",
        }
    )

    await save_refresh_token(
        user_id=1,
        session_id="test-session",
        token=refresh_token,
        expire_seconds=60,
    )
    token_jti = "test-jti"
    token_exp = int(datetime.now(UTC).timestamp()) + 60
    result = await logout_user(
        user_id=1,
        session_id="test-session",
        token_jti=token_jti,
        token_exp=token_exp,
    )
    assert result == {
        "message": "Successfully logged out",
    }

    stored_token = await get_refresh_token(
        1,
        "test-session",
    )

    assert stored_token is None
    assert await is_token_blacklisted("test-jti") is True


@pytest.mark.asyncio
async def test_logout_user_with_expired_token(redis_client: Redis):
    refresh_token = create_refresh_token(
        data={
            "sub": "1",
            "email": "test@example.com",
            "session_id": "expired-session",
        }
    )

    await save_refresh_token(
        user_id=1,
        session_id="expired-session",
        token=refresh_token,
        expire_seconds=60,
    )
    token_jti = "expired-test-jti"
    token_exp = int(datetime.now(UTC).timestamp()) - 60
    result = await logout_user(
        user_id=1,
        session_id="expired-session",
        token_jti=token_jti,
        token_exp=token_exp,
    )
    assert result == {
        "message": "Successfully logged out",
    }

    stored_token = await get_refresh_token(
        1,
        "expired-session",
    )

    assert stored_token is None
    assert await is_token_blacklisted("expired-test-jti") is False


@pytest.mark.asyncio
async def test_logout_user_without_refresh_token(redis_client: Redis):
    token_jti = "no-refresh-token-jti"
    token_exp = int(datetime.now(UTC).timestamp()) + 60
    result = await logout_user(
        user_id=1,
        session_id="not-found-session",
        token_jti=token_jti,
        token_exp=token_exp,
    )
    assert result == {
        "message": "Successfully logged out",
    }

    assert await is_token_blacklisted("no-refresh-token-jti") is True


@pytest.mark.asyncio
async def test_logout_all_users(redis_client: Redis):
    await save_refresh_token(
        user_id=1,
        session_id="session-a",
        token="token-a",
        expire_seconds=60,
    )

    await save_refresh_token(
        user_id=1,
        session_id="session-b",
        token="token-b",
        expire_seconds=60,
    )

    await save_refresh_token(
        user_id=1,
        session_id="session-c",
        token="token-c",
        expire_seconds=60,
    )
    await save_refresh_token(
        user_id=2,
        session_id="session-x",
        token="token-x",
        expire_seconds=60,
    )
    result = await logout_all_users(1)
    assert result == {
        "message": "Successfully logged out from all devices",
    }
    assert await get_refresh_token(1, "session-a") is None
    assert await get_refresh_token(1, "session-b") is None
    assert await get_refresh_token(1, "session-c") is None
    assert await get_refresh_token(2, "session-x") == "token-x"
