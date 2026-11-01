import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    InvalidCredentials,
    InvalidRefreshToken,
    InvalidSession,
    InvalidToken,
    PasswordTooShort,
    UserAlreadyExists,
)
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
)
from app.core.token_blacklist import is_token_blacklisted
from app.features.auth.service import (
    TokenPair,
    login_user,
    logout_all_users,
    logout_user,
    refresh_access_token,
    register_user,
)
from app.features.sessions.entities import Session
from app.features.sessions.service import create_session
from app.features.sessions.session_store import delete_all_sessions, get_session
from app.features.users.models import User, UserProfile
from app.features.users.repository import SQLAlchemyUserRepository
from app.features.users.service import get_user_by_email

# در صورتی که کلاس‌های خطای تو دیگر از HTTPException ارث‌بری نمی‌کنند (الگوی AppError)،
# این تاپل باعث می‌شود تست‌ها چه با AppError و چه با HTTPException بدون خطا کار کنند:
EXPECTED_AUTH_ERRORS = (
    HTTPException,
    UserAlreadyExists,
    InvalidCredentials,
    InvalidRefreshToken,
    InvalidSession,
    InvalidToken,
)


@pytest.fixture
def user_repo(db_session: AsyncSession) -> SQLAlchemyUserRepository:
    return SQLAlchemyUserRepository(db_session)


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
async def test_success_register_user(user_repo: SQLAlchemyUserRepository):
    email = "register@example.com"
    password = "StrongPassword123@"

    created_user = await register_user(
        user_repo,
        email=email,
        password=password,
    )

    assert created_user is not None
    assert created_user.email == email
    assert created_user.is_active is True
    assert created_user.password_hash != password


@pytest.mark.asyncio
async def test_register_user_with_existing_email(
    db_session: AsyncSession,
    user_repo: SQLAlchemyUserRepository,
):
    existing_user = User(
        email="duplicate@example.com",
        password_hash="hashed_password",
        is_active=True,
    )

    db_session.add(existing_user)
    await db_session.commit()

    with pytest.raises(EXPECTED_AUTH_ERRORS) as exc_info:
        await register_user(
            user_repo,
            email="duplicate@example.com",
            password="StrongPassword123",
        )

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_successful_login(
    db_session: AsyncSession,
    user_repo: SQLAlchemyUserRepository,
    redis_client: Redis,
):
    existing_user = User(
        email="login@example.com",
        password_hash=hash_password("StrongPassword123"),
        is_active=True,
    )

    db_session.add(existing_user)
    await db_session.commit()

    result = await login_user(
        user_repo,
        email="login@example.com",
        password="StrongPassword123",
    )

    assert isinstance(result, TokenPair)
    assert result.access_token
    assert result.refresh_token

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
    user_repo: SQLAlchemyUserRepository,
):
    with pytest.raises(EXPECTED_AUTH_ERRORS) as exc_info:
        await login_user(
            user_repo,
            email="not-found@example.com",
            password="StrongPassword123",
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_user_wrong_password(
    db_session: AsyncSession,
    user_repo: SQLAlchemyUserRepository,
):
    existing_user = User(
        email="login@example.com",
        password_hash=hash_password("StrongPassword123"),
        is_active=True,
    )

    db_session.add(existing_user)
    await db_session.commit()

    with pytest.raises(EXPECTED_AUTH_ERRORS) as exc_info:
        await login_user(
            user_repo,
            email="login@example.com",
            password="wrongpassword",
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid credentials"


@pytest.mark.asyncio
async def test_refresh_access_token_without_user_id(
    user_repo: SQLAlchemyUserRepository,
):
    refresh_token = create_refresh_token(
        data={
            "email": "test@example.com",
            "session_id": "test-session",
        },
        jti=str(uuid4()),
    )

    with pytest.raises(EXPECTED_AUTH_ERRORS) as exc_info:
        await refresh_access_token(user_repo, refresh_token=refresh_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid refresh token"


@pytest.mark.asyncio
async def test_refresh_access_token_without_session_id(
    user_repo: SQLAlchemyUserRepository,
):
    refresh_token = create_refresh_token(
        data={
            "sub": "1",
            "email": "test@example.com",
        },
        jti=str(uuid4()),
    )

    with pytest.raises(EXPECTED_AUTH_ERRORS) as exc_info:
        await refresh_access_token(user_repo, refresh_token=refresh_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid refresh token"


@pytest.mark.asyncio
async def test_refresh_access_token_token_not_found(
    redis_client: Redis,
    db_session: AsyncSession,
    user_repo: SQLAlchemyUserRepository,
):
    user = User(
        email="test@example.com",
        password_hash=hash_password("StrongPassword123"),
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    refresh_token = create_refresh_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "session_id": "not-found-session-001",
        },
        jti=str(uuid4()),
    )

    with pytest.raises(EXPECTED_AUTH_ERRORS) as exc_info:
        await refresh_access_token(user_repo, refresh_token=refresh_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid session"


@pytest.mark.asyncio
async def test_refresh_access_token_token_mismatch(
    redis_client: Redis,
    db_session: AsyncSession,
    user_repo: SQLAlchemyUserRepository,
):
    user = User(
        email="test@example.com",
        password_hash=hash_password("StrongPassword123"),
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    correct_jti = str(uuid4())
    wrong_jti = str(uuid4())

    session = await create_test_session(
        user_id=user.id,
        jti=correct_jti,
    )

    wrong_token = create_refresh_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "session_id": str(session.session_id),
        },
        jti=wrong_jti,
        expires_delta=timedelta(days=2),
    )

    with pytest.raises(EXPECTED_AUTH_ERRORS) as exc_info:
        await refresh_access_token(user_repo, refresh_token=wrong_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid token"


@pytest.mark.asyncio
async def test_successful_refresh_access_token(
    redis_client: Redis,
    db_session: AsyncSession,
    user_repo: SQLAlchemyUserRepository,
):
    user = User(
        email="test@example.com",
        password_hash=hash_password("StrongPassword123"),
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    old_jti = str(uuid4())

    session = await create_test_session(
        user_id=user.id,
        jti=old_jti,
    )

    refresh_token = create_refresh_token(
        data={
            "sub": str(user.id),
            "email": "test@example.com",
            "session_id": str(session.session_id),
        },
        jti=old_jti,
    )

    result = await refresh_access_token(user_repo, refresh_token=refresh_token)

    assert isinstance(result, TokenPair)
    assert result.access_token
    assert result.refresh_token
    assert result.refresh_token != refresh_token

    new_payload = decode_refresh_token(
        result.refresh_token,
    )

    assert new_payload["session_id"] == str(session.session_id)
    assert new_payload["sub"] == str(user.id)
    assert new_payload["jti"] != old_jti

    updated_session = await get_session(
        user.id,
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

    await logout_user(
        user_id=1,
        session_id=str(session.session_id),
        token_jti=token_jti,
        token_exp=token_exp,
    )

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

    await logout_user(
        user_id=1,
        session_id=str(session.session_id),
        token_jti=token_jti,
        token_exp=token_exp,
    )

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

    await logout_user(
        user_id=1,
        session_id="not-found-session",
        token_jti=token_jti,
        token_exp=int(datetime.now(UTC).timestamp()) + 60,
    )

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

    await logout_all_users(1)

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


@pytest.mark.asyncio
async def test_register_user_rejects_email_with_different_case(
    user_repo: SQLAlchemyUserRepository,
):
    created_user = await register_user(
        user_repo,
        email="Test@Example.com",
        password="StrongPassword123@",
    )

    assert created_user.email == "test@example.com"

    with pytest.raises(UserAlreadyExists):
        await register_user(
            user_repo,
            email="test@example.com",
            password="StrongPassword123@",
        )


@pytest.mark.asyncio
async def test_login_user_accepts_email_with_different_case(
    user_repo: SQLAlchemyUserRepository,
    redis_client: Redis,
):
    await register_user(
        user_repo,
        email="Test@Example.com",
        password="StrongPassword123@",
    )

    token = await login_user(
        user_repo,
        email="TEST@EXAMPLE.COM",
        password="StrongPassword123@",
    )

    assert token is not None


@pytest.mark.asyncio
async def test_register_user_handles_integrity_error(
    db_session: AsyncSession,
    user_repo: SQLAlchemyUserRepository,
):
    existing_user = User(
        email="race@example.com",
        password_hash="hashed_password",
        is_active=True,
    )
    db_session.add(existing_user)
    await db_session.commit()

    with (
        patch(
            "app.features.auth.service.get_user_by_email",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            user_repo,
            "get_by_email",
            new=AsyncMock(return_value=None),
        ),
    ):
        with pytest.raises(EXPECTED_AUTH_ERRORS) as exc_info:
            await register_user(
                user_repo,
                email="race@example.com",
                password="StrongPassword123@",
            )

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_register_user_rolls_back_after_integrity_error(
    db_session: AsyncSession,
    user_repo: SQLAlchemyUserRepository,
):
    existing_user = User(
        email="rollback@example.com",
        password_hash="hashed_password",
        is_active=True,
    )
    db_session.add(existing_user)
    await db_session.commit()

    with (
        patch(
            "app.features.auth.service.get_user_by_email",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            user_repo,
            "get_by_email",
            new=AsyncMock(return_value=None),
        ),
    ):
        with pytest.raises(EXPECTED_AUTH_ERRORS) as exc_info:
            await register_user(
                user_repo,
                email="rollback@example.com",
                password="StrongPassword123@",
            )

    assert exc_info.value.status_code == 409

    new_user = User(
        email="after-error@example.com",
        password_hash="hashed_password",
        is_active=True,
    )
    db_session.add(new_user)
    await db_session.commit()

    assert new_user.id is not None


@pytest.mark.asyncio
async def test_refresh_access_token_with_malformed_user_id(
    user_repo: SQLAlchemyUserRepository,
):
    refresh_token = create_refresh_token(
        data={
            "sub": "not-an-integer",
            "email": "test@example.com",
            "session_id": "test-session",
        },
        jti=str(uuid4()),
    )

    with pytest.raises(EXPECTED_AUTH_ERRORS) as exc_info:
        await refresh_access_token(user_repo, refresh_token=refresh_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid refresh token"


@pytest.mark.asyncio
async def test_concurrent_refresh_access_token_allows_only_one_refresh(
    redis_client: Redis,
    db_session: AsyncSession,
    user_repo: SQLAlchemyUserRepository,
):
    user = User(
        email="test@example.com",
        password_hash=hash_password("StrongPassword123"),
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    old_jti = str(uuid4())

    session = await create_test_session(
        user_id=user.id,
        jti=old_jti,
    )

    refresh_token = create_refresh_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "session_id": str(session.session_id),
        },
        jti=old_jti,
    )

    results = await asyncio.gather(
        refresh_access_token(user_repo, refresh_token=refresh_token),
        refresh_access_token(user_repo, refresh_token=refresh_token),
        return_exceptions=True,
    )

    successful = [result for result in results if not isinstance(result, Exception)]

    failed = [result for result in results if isinstance(result, EXPECTED_AUTH_ERRORS)]

    assert len(successful) == 1
    assert len(failed) == 1
    assert failed[0].status_code == 401
    assert failed[0].detail == "Invalid token"


@pytest.mark.asyncio
async def test_logout_all_can_delete_session_created_during_logout_all(
    redis_client: Redis,
    monkeypatch: pytest.MonkeyPatch,
):
    user_id = 1

    old_session = await create_test_session(
        user_id=user_id,
        jti=str(uuid4()),
    )

    scan_started = asyncio.Event()
    login_completed = asyncio.Event()

    old_key = f"session:{user_id}:{old_session.session_id}"

    new_session = None
    new_key = None

    async def controlled_scan_iter(match):
        assert match == f"session:{user_id}:*"

        yield old_key

        scan_started.set()
        await login_completed.wait()

        yield new_key

    async def login():
        nonlocal new_session, new_key

        new_session = await create_session(
            user_id=user_id,
            jti=str(uuid4()),
            device=None,
            ip_address=None,
            expire_seconds=60,
        )

        new_key = f"session:{user_id}:{new_session.session_id}"
        login_completed.set()

    monkeypatch.setattr(
        redis_client,
        "scan_iter",
        controlled_scan_iter,
    )

    logout_task = asyncio.create_task(
        delete_all_sessions(user_id),
    )

    await scan_started.wait()

    await login()
    await logout_task

    assert new_session is not None

    remaining_session = await get_session(
        user_id,
        str(new_session.session_id),
    )

    assert remaining_session is None


@pytest.mark.asyncio
async def test_login_with_nonexistent_email_verifies_dummy_password_hash(
    user_repo: SQLAlchemyUserRepository,
    monkeypatch: pytest.MonkeyPatch,
):
    verify_called = False

    async def fake_get_user_by_email(repo, email):
        return None

    def fake_verify_password(password, password_hash):
        nonlocal verify_called

        verify_called = True

        assert password_hash == DUMMY_PASSWORD_HASH

        return False

    monkeypatch.setattr(
        "app.features.auth.service.get_user_by_email",
        fake_get_user_by_email,
    )
    monkeypatch.setattr(
        "app.features.auth.service.verify_password",
        fake_verify_password,
    )

    with pytest.raises(InvalidCredentials):
        await login_user(
            user_repo,
            email="nonexistent@example.com",
            password="wrong-password",
        )

    assert verify_called is True


@pytest.mark.asyncio
async def test_login_with_existing_user_verifies_real_password_hash(
    user_repo: SQLAlchemyUserRepository,
    monkeypatch: pytest.MonkeyPatch,
):
    password_hash = "real-password-hash"
    user = SimpleNamespace(
        password_hash=password_hash,
        is_active=True,
        id=123,
    )

    async def fake_get_user_by_email(repo, email):
        return user

    def fake_verify_password(password, hashed_password):
        assert hashed_password == password_hash
        return False

    monkeypatch.setattr(
        "app.features.auth.service.get_user_by_email",
        fake_get_user_by_email,
    )
    monkeypatch.setattr(
        "app.features.auth.service.verify_password",
        fake_verify_password,
    )

    with pytest.raises(InvalidCredentials):
        await login_user(
            user_repo,
            email="existing@example.com",
            password="wrong-password",
        )


@pytest.mark.asyncio
async def test_register_user_rejects_password_shorter_than_policy(
    user_repo: SQLAlchemyUserRepository,
):
    email = "short-password@example.com"
    password = "StrongPassword123@"

    with patch(
        "app.features.auth.service.password_policy.validate",
        side_effect=PasswordTooShort(),
    ) as mock_validate:
        with pytest.raises(PasswordTooShort):
            await register_user(user_repo, email=email, password=password)

    mock_validate.assert_called_once_with(password)

    user = await get_user_by_email(
        user_repo,
        email,
    )
    assert user is None


@pytest.mark.asyncio
async def test_register_user_creates_profile(
    db_session: AsyncSession,
    user_repo: SQLAlchemyUserRepository,
) -> None:
    user = await register_user(
        user_repo,
        email="profile-test@example.com",
        password="StrongPassword123!",
    )

    result = await db_session.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()

    assert profile is not None
    assert profile.user_id == user.id
    assert profile.first_name is None
    assert profile.last_name is None
    assert profile.avatar_url is None


@pytest.mark.asyncio
async def test_register_user_rolls_back_when_profile_creation_fails(
    db_session: AsyncSession,
    user_repo: SQLAlchemyUserRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_profile_init(*args, **kwargs):
        raise RuntimeError("Profile creation failed")

    monkeypatch.setattr(
        "app.features.users.repository.UserProfile",
        fail_profile_init,
    )

    email = "rollback-test@example.com"

    with pytest.raises(RuntimeError, match="Profile creation failed"):
        await register_user(
            user_repo,
            email=email,
            password="StrongPassword123!",
        )

    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    assert user is None
