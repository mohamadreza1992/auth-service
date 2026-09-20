from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    InvalidCredentials,
    InvalidToken,
    RevokedToken,
)
from app.core.security import decode_access_token
from app.core.token_blacklist import is_token_blacklisted
from app.database.session import get_db
from app.features.auth.models import User
from app.features.auth.repository import get_user_by_id
from app.features.sessions.service import refresh_session_activity
from app.features.sessions.session_validation import validate_session


@dataclass
class AuthContext:
    user: User
    session_id: str
    token_jti: str
    token_exp: int


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise InvalidCredentials() from None

    user_id = payload.get("sub")
    session_id = payload.get("session_id")
    jti = payload.get("jti")
    exp = payload.get("exp")

    if exp is None:
        raise InvalidToken()

    if not isinstance(exp, int):
        raise InvalidToken()

    if jti is None:
        raise InvalidToken()

    if not isinstance(jti, str) or not jti:
        raise InvalidToken()

    if await is_token_blacklisted(jti):
        raise RevokedToken()

    if session_id is None:
        raise InvalidCredentials()

    if not isinstance(session_id, str) or not session_id:
        raise InvalidCredentials()

    if user_id is None:
        raise InvalidCredentials()

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise InvalidCredentials() from None

    await refresh_session_activity(user_id, session_id)
    await validate_session(user_id, session_id)

    user = await get_user_by_id(
        db,
        user_id,
    )

    if user is None:
        raise InvalidCredentials()

    if not user.is_active:
        raise InvalidCredentials()

    return AuthContext(
        user=user,
        session_id=session_id,
        token_jti=jti,
        token_exp=exp,
    )
