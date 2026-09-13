import uuid
from datetime import UTC, datetime

from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    InvalidCredentials,
    InvalidRefreshToken,
    UserAlreadyExists,
)
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.core.token_blacklist import blacklist_token
from app.features.auth.models import User
from app.features.auth.repository import (
    create_user,
    get_user_by_email,
)
from app.features.auth.schemas import RefreshTokenRequest, Token, UserCreate, UserLogin
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

    user = await create_user(
        db,
        user,
    )
    await db.commit()
    return user


async def login_user(
    db: AsyncSession,
    user_data: UserLogin,
) -> Token:
    user = await get_user_by_email(
        db,
        user_data.email,
    )
    if not user:
        raise InvalidCredentials()

    if not verify_password(
        user_data.password,
        user.password_hash,
    ):
        raise InvalidCredentials()

    if not user.is_active:
        raise InvalidCredentials()

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
            "email": user.email,
            "session_id": session_id,
        },
    )

    refresh_token = create_refresh_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "session_id": session_id,
        },
        jti=jti,
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


async def refresh_access_token(data: RefreshTokenRequest):
    try:
        payload = decode_refresh_token(data.refresh_token)
    except JWTError:
        raise InvalidRefreshToken() from None

    user_id = payload.get("sub")
    email = payload.get("email")
    session_id = payload.get("session_id")
    jti = payload.get("jti")

    if user_id is None:
        raise InvalidRefreshToken()
    if session_id is None:
        raise InvalidRefreshToken()

    if jti is None:
        raise InvalidRefreshToken()

    session = await validate_session(int(user_id), session_id)

    await validate_session_jti(session, jti)

    access_token = create_access_token(
        data={
            "sub": user_id,
            "email": email,
            "session_id": session_id,
        }
    )
    new_jti = str(uuid.uuid4())
    new_refresh_token = create_refresh_token(
        data={
            "sub": user_id,
            "email": email,
            "session_id": session_id,
        },
        jti=new_jti,
    )

    await rotate_session_jti(
        user_id=int(user_id),
        session_id=session_id,
        jti=new_jti,
    )

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
