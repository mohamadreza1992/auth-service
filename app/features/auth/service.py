import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from jose import JWTError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    InvalidCredentials,
    InvalidRefreshToken,
    InvalidToken,
    UserAlreadyExists,
)
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
from app.features.auth.password.policy import PasswordPolicy
from app.features.sessions.service import (
    create_session,
    get_validated_session,
    revoke_all_sessions,
    revoke_session,
    rotate_session_jti,
    run_with_session_lock,
)
from app.features.users.models import User, UserProfile
from app.features.users.service import (
    create_profile,
    create_user,
    get_user_by_email,
    get_user_by_id,
)

logger = get_logger(__name__)


password_policy = PasswordPolicy()


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str


async def register_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
) -> User:
    normalized_email = email.strip().lower()

    existing_user = await get_user_by_email(db, normalized_email)

    if existing_user:
        raise UserAlreadyExists()

    password_policy.validate(password)

    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        is_active=True,
    )

    try:
        user = await create_user(db, user)

        await create_profile(
            db,
            UserProfile(user_id=user.id),
        )

        await db.commit()
        return user

    except IntegrityError as exc:
        await db.rollback()
        raise UserAlreadyExists() from exc
    except Exception:
        await db.rollback()
        raise


async def login_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
) -> TokenPair:
    normalized_email = email.strip().lower()

    user = await get_user_by_email(
        db,
        normalized_email,
    )

    password_hash_to_verify = user.password_hash if user else DUMMY_PASSWORD_HASH

    if not verify_password(
        password,
        password_hash_to_verify,
    ):
        raise InvalidCredentials()

    if not user:
        raise InvalidCredentials()

    if not user.is_active:
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
    db: AsyncSession,
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
        db,
        user_id,
    )

    if user is None:
        raise InvalidRefreshToken()

    if not user.is_active:
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
