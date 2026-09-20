import uuid
from datetime import UTC, datetime

from jose import JWTError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    InvalidCredentials,
    InvalidRefreshToken,
    SessionOperationInProgress,
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
from app.core.token_blacklist import blacklist_token
from app.features.auth.models import User
from app.features.auth.repository import create_user, get_user_by_email, get_user_by_id
from app.features.auth.schemas import RefreshTokenRequest, Token, UserCreate, UserLogin
from app.features.sessions.lock import (
    acquire_session_lock,
    release_session_lock,
)
from app.features.sessions.service import (
    create_session,
    revoke_all_sessions,
    revoke_session,
    rotate_session_jti,
)
from app.features.sessions.session_validation import (
    validate_session,
    validate_session_jti,
)

logger = get_logger(__name__)


async def register_user(
    db: AsyncSession,
    user_data: UserCreate,
) -> User:
    existing_user = await get_user_by_email(
        db,
        user_data.email,
    )

    if existing_user:
        raise UserAlreadyExists()

    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        is_active=True,
    )
    try:
        user = await create_user(
            db,
            user,
        )
        await db.commit()
        return user
    except IntegrityError as exc:
        await db.rollback()
        raise UserAlreadyExists() from exc


async def login_user(
    db: AsyncSession,
    user_data: UserLogin,
) -> Token:
    user = await get_user_by_email(
        db,
        user_data.email,
    )

    password_hash_to_verify = user.password_hash if user else DUMMY_PASSWORD_HASH

    if not verify_password(
        user_data.password,
        password_hash_to_verify,
    ):
        raise InvalidCredentials()

    if not user:
        raise InvalidCredentials()

    if not user.is_active:
        raise InvalidCredentials()

    lock_token = await acquire_session_lock(user.id)

    if lock_token is None:
        raise SessionOperationInProgress()

    try:
        jti = str(uuid.uuid4())

        session = await create_session(
            user_id=user.id,
            jti=jti,
            device=None,
            ip_address=None,
            expire_seconds=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
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

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )
    finally:
        await release_session_lock(
            user.id,
            lock_token,
        )


async def refresh_access_token(db: AsyncSession, data: RefreshTokenRequest):
    try:
        payload = decode_refresh_token(data.refresh_token)
    except JWTError:
        raise InvalidRefreshToken() from None

    user_id = payload.get("sub")
    session_id = payload.get("session_id")
    jti = payload.get("jti")

    if user_id is None:
        raise InvalidRefreshToken()

    if not isinstance(session_id, str) or not session_id:
        raise InvalidRefreshToken()

    if not isinstance(jti, str) or not jti:
        raise InvalidRefreshToken()
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise InvalidRefreshToken() from None
    user = await get_user_by_id(db, user_id)

    if user is None:
        raise InvalidRefreshToken()
    if not user.is_active:
        raise InvalidRefreshToken()

    session = await validate_session(user_id, session_id)

    await validate_session_jti(session, jti)

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

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


async def logout_user(user_id: int, session_id: str, token_jti: str, token_exp: int):
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

    return {"message": "Successfully logged out"}


async def logout_all_users(user_id: int):
    await revoke_all_sessions(user_id)

    return {
        "message": "Successfully logged out from all devices",
    }
