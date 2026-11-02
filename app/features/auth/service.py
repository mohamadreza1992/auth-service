import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from jose import JWTError

from app.core.config import settings
from app.core.exceptions import InvalidToken
from app.core.logging import get_logger
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.core.token_blacklist import (
    blacklist_token,
    get_refresh_token_rotation_time,
    mark_refresh_token_rotated,
)
from app.features.auth.exceptions import (
    InvalidCredentials,
    InvalidRefreshToken,
)
from app.features.auth.password.policy import PasswordPolicy
from app.features.sessions.service import (
    create_session,
    get_validated_session,
    revoke_all_sessions,
    revoke_session,
    rotate_session_jti,
    run_with_session_lock,
)
from app.features.users.entities import UserEntity
from app.features.users.exceptions import UserAlreadyExists
from app.features.users.ports import UserRepository
from app.features.users.service import (
    create_user_with_profile,
    get_user_by_email,
    get_user_by_id,
)

logger = get_logger(__name__)

password_policy = PasswordPolicy()


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str


async def register_user(
    user_repository: UserRepository,
    *,
    email: str,
    password: str,
) -> UserEntity:
    normalized_email = email.strip().lower()

    existing_user = await get_user_by_email(user_repository, normalized_email)
    if existing_user:
        raise UserAlreadyExists()

    password_policy.validate(password)

    hashed_password = await asyncio.to_thread(hash_password, password)

    return await create_user_with_profile(
        user_repository,
        email=normalized_email,
        password_hash=hashed_password,
    )


async def login_user(
    user_repository: UserRepository,
    *,
    email: str,
    password: str,
) -> TokenPair:
    normalized_email = email.strip().lower()

    user = await get_user_by_email(
        user_repository,
        normalized_email,
    )

    password_hash_to_verify = user.password_hash if user else DUMMY_PASSWORD_HASH

    is_valid = await asyncio.to_thread(
        verify_password,
        password,
        password_hash_to_verify,
    )

    if not is_valid or not user or not user.is_active:
        raise InvalidCredentials()

    async def create_login_tokens() -> TokenPair:
        jti = str(uuid.uuid4())

        session = await create_session(
            user_id=user.id,
            jti=jti,
            device=None,
            ip_address=None,
            expire_seconds=(settings.jwt_refresh_token_expire_days * 24 * 60 * 60),
        )

        session_id = str(session.session_id)

        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "session_id": session_id,
            },
        )

        refresh_token = create_refresh_token(
            data={
                "sub": str(user.id),
                "session_id": session_id,
            },
            jti=jti,
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    return await run_with_session_lock(
        user.id,
        create_login_tokens,
    )


async def refresh_access_token(
    user_repository: UserRepository,
    *,
    refresh_token: str,
) -> TokenPair:
    request_started_at = datetime.now(UTC).timestamp()

    try:
        payload = decode_refresh_token(refresh_token)
    except JWTError:
        raise InvalidRefreshToken() from None

    user_id = payload.get("sub")
    session_id = payload.get("session_id")
    jti = payload.get("jti")
    exp = payload.get("exp")

    if user_id is None:
        raise InvalidRefreshToken()

    if not isinstance(session_id, str) or not session_id:
        raise InvalidRefreshToken()

    if not isinstance(jti, str) or not jti:
        raise InvalidRefreshToken()

    if not isinstance(exp, int):
        raise InvalidRefreshToken()

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise InvalidRefreshToken() from None

    user = await get_user_by_id(
        user_repository,
        user_id,
    )

    if user is None or not user.is_active:
        raise InvalidRefreshToken()

    session = await get_validated_session(
        user_id,
        session_id,
    )

    if session.jti != jti:
        rotation_time = await get_refresh_token_rotation_time(jti)

        if rotation_time is not None and request_started_at > rotation_time:
            await revoke_session(
                user_id,
                session_id,
            )

        raise InvalidToken()

    access_token = create_access_token(
        data={
            "sub": str(user_id),
            "session_id": session_id,
        }
    )

    new_jti = str(uuid.uuid4())

    new_refresh_token = create_refresh_token(
        data={
            "sub": str(user_id),
            "session_id": session_id,
        },
        jti=new_jti,
    )

    updated = await rotate_session_jti(
        user_id=user_id,
        session_id=session_id,
        expected_jti=jti,
        new_jti=new_jti,
    )

    if not updated:
        raise InvalidRefreshToken()

    remaining_time = exp - int(datetime.now(UTC).timestamp())

    if remaining_time > 0:
        await mark_refresh_token_rotated(
            jti,
            remaining_time,
        )

    return TokenPair(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


async def logout_user(
    user_id: int,
    session_id: str,
    token_jti: str,
    token_exp: int,
) -> None:
    await revoke_session(
        user_id,
        session_id,
    )
    logger.info(
        "User logged out",
        extra={
            "user_id": user_id,
            "session_id": session_id,
        },
    )

    remaining_time = token_exp - int(datetime.now(UTC).timestamp())

    if remaining_time > 0:
        await blacklist_token(
            token_jti,
            remaining_time,
        )


async def logout_all_users(user_id: int) -> None:
    await revoke_all_sessions(user_id)
