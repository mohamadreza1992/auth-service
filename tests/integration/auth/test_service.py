from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_refresh_token,
    decode_refresh_token,
    hash_password,
)
from app.core.token_blacklist import is_token_blacklisted
from app.features.auth.models import User
from app.features.auth.schemas import RefreshTokenRequest, UserCreate, UserLogin
from app.features.auth.service import (
    login_user,
    logout_all_users,
    logout_user,
    refresh_access_token,
    register_user,
)
from app.features.sessions.schemas import Session
from app.features.sessions.service import create_session
from app.features.sessions.session_store import get_session


async def create_test_session(
    user_id: int,
    jti: str,
    expire_seconds: int = 60,
) -> Session:
    return await create_session(
        user_id=user_id,
        jti=jti,
        device=None,
        ip_address=None,
        expire_seconds=expire_seconds,
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
async def test_register_user_with_existing_email(
    db_session: AsyncSession,
):
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
        await register_user(
            db_session,
            user_data,
        )

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

    result = await login_user(
        db_session,
        user_data,
    )

    assert result.access_token
    assert result.refresh_token
    assert result.token_type == "bearer"

    payload = decode_refresh_token(result.refresh_token)

    session = await get_session(
        int(payload["sub"]),
        payload["session_id"],
    )

    assert session is not None
    assert str(session.session_id) == payload["session_id"]
    assert session.user_id == int(payload["sub"])
    assert session.jti == payload["jti"]


@pytest.mark.asyncio
async def test_login_user_not_found(
    db_session: AsyncSession,
):
    user_data = UserLogin(
        email="not-found@example.com",
        password="StrongPassword123",
    )

    with pytest.raises(HTTPException) as exc_info:
        await login_user(
            db_session,
            user_data,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_user_wrong_password(
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
        password="wrongpassword",
    )

    with pytest.raises(HTTPException) as exc_info:
        await login_user(
            db_session,
            user_data,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid credentials"


@pytest.mark.asyncio
async def test_refresh_access_token_without_user_id():
    refresh_token = create_refresh_token(
        data={
            "email": "test@example.com",
            "session_id": "test-session",
        },
        jti=str(uuid4()),
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
        },
        jti=str(uuid4()),
    )

    data = RefreshTokenRequest(
        refresh_token=refresh_token,
    )

    with pytest.raises(HTTPException) as exc_info:
        await refresh_access_token(data)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid refresh token"


@pytest.mark.asyncio
async def test_refresh_access_token_token_not_found(
    redis_client: Redis,
):
    refresh_token = create_refresh_token(
        data={
            "sub": "1",
            "email": "test@example.com",
            "session_id": "not-found-session-001",
        },
        jti=str(uuid4()),
    )

    data = RefreshTokenRequest(
        refresh_token=refresh_token,
    )

    with pytest.raises(HTTPException) as exc_info:
        await refresh_access_token(data)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid session"


@pytest.mark.asyncio
async def test_refresh_access_token_token_mismatch(
    redis_client: Redis,
):
    correct_jti = str(uuid4())
    wrong_jti = str(uuid4())

    session = await create_test_session(
        user_id=1,
        jti=correct_jti,
    )

    wrong_token = create_refresh_token(
        data={
            "sub": "1",
            "email": "test@example.com",
            "session_id": str(session.session_id),
        },
        jti=wrong_jti,
        expires_delta=timedelta(days=2),
    )

    data = RefreshTokenRequest(
        refresh_token=wrong_token,
    )

    with pytest.raises(HTTPException) as exc_info:
        await refresh_access_token(data)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid token"


@pytest.mark.asyncio
async def test_successful_refresh_access_token(
    redis_client: Redis,
):
    old_jti = str(uuid4())

    session = await create_test_session(
        user_id=1,
        jti=old_jti,
    )

    refresh_token = create_refresh_token(
        data={
            "sub": "1",
            "email": "test@example.com",
            "session_id": str(session.session_id),
        },
        jti=old_jti,
    )

    data = RefreshTokenRequest(
        refresh_token=refresh_token,
    )

    result = await refresh_access_token(data)

    assert result.access_token
    assert result.refresh_token
    assert result.refresh_token != refresh_token

    new_payload = decode_refresh_token(
        result.refresh_token,
    )

    assert new_payload["session_id"] == str(session.session_id)
    assert new_payload["sub"] == "1"
    assert new_payload["jti"] != old_jti

    updated_session = await get_session(
        1,
        str(session.session_id),
    )

    assert updated_session is not None
    assert updated_session.jti == new_payload["jti"]


@pytest.mark.asyncio
async def test_successful_logout_user(
    redis_client: Redis,
):
    token_jti = str(uuid4())

    session = await create_test_session(
        user_id=1,
        jti=token_jti,
    )

    token_exp = int(datetime.now(UTC).timestamp()) + 60

    result = await logout_user(
        user_id=1,
        session_id=str(session.session_id),
        token_jti=token_jti,
        token_exp=token_exp,
    )

    assert result == {
        "message": "Successfully logged out",
    }

    stored_session = await get_session(
        1,
        str(session.session_id),
    )

    assert stored_session is None
    assert await is_token_blacklisted(token_jti) is True


@pytest.mark.asyncio
async def test_logout_user_with_expired_token(
    redis_client: Redis,
):
    token_jti = str(uuid4())

    session = await create_test_session(
        user_id=1,
        jti=token_jti,
    )

    token_exp = int(datetime.now(UTC).timestamp()) - 60

    result = await logout_user(
        user_id=1,
        session_id=str(session.session_id),
        token_jti=token_jti,
        token_exp=token_exp,
    )

    assert result == {
        "message": "Successfully logged out",
    }

    stored_session = await get_session(
        1,
        str(session.session_id),
    )

    assert stored_session is None
    assert await is_token_blacklisted(token_jti) is False


@pytest.mark.asyncio
async def test_logout_user_without_refresh_token(
    redis_client: Redis,
):
    token_jti = str(uuid4())

    result = await logout_user(
        user_id=1,
        session_id="not-found-session",
        token_jti=token_jti,
        token_exp=int(datetime.now(UTC).timestamp()) + 60,
    )

    assert result == {
        "message": "Successfully logged out",
    }

    assert await is_token_blacklisted(token_jti) is True


@pytest.mark.asyncio
async def test_logout_all_users(
    redis_client: Redis,
):
    session_a = await create_test_session(
        user_id=1,
        jti=str(uuid4()),
    )

    session_b = await create_test_session(
        user_id=1,
        jti=str(uuid4()),
    )

    session_c = await create_test_session(
        user_id=1,
        jti=str(uuid4()),
    )

    session_x = await create_test_session(
        user_id=2,
        jti=str(uuid4()),
    )

    result = await logout_all_users(1)

    assert result == {
        "message": "Successfully logged out from all devices",
    }

    assert (
        await get_session(
            1,
            str(session_a.session_id),
        )
        is None
    )

    assert (
        await get_session(
            1,
            str(session_b.session_id),
        )
        is None
    )

    assert (
        await get_session(
            1,
            str(session_c.session_id),
        )
        is None
    )

    assert (
        await get_session(
            2,
            str(session_x.session_id),
        )
        is not None
    )
