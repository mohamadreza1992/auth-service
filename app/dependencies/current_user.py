from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from app.core.exceptions import (
    InvalidCredentials,
    InvalidToken,
    RevokedToken,
)
from app.core.security import decode_access_token
from app.core.token_blacklist import is_token_blacklisted
from app.features.sessions.service import (
    get_validated_session,
    refresh_session_activity,
)
from app.features.users.dependencies import UserRepoDep
from app.features.users.entities import UserEntity
from app.features.users.service import get_user_by_id


@dataclass(frozen=True, slots=True)
class AuthContext:
    user: UserEntity
    session_id: str
    token_jti: str
    token_exp: int


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
)

TokenDep = Annotated[str, Depends(oauth2_scheme)]


async def get_current_user(
    token: TokenDep,
    user_repository: UserRepoDep,
) -> AuthContext:
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise InvalidCredentials() from None

    user_id = payload.get("sub")
    session_id = payload.get("session_id")
    jti = payload.get("jti")
    exp = payload.get("exp")

    if not isinstance(exp, int):
        raise InvalidToken()

    if not isinstance(jti, str) or not jti:
        raise InvalidToken()

    if await is_token_blacklisted(jti):
        raise RevokedToken()

    if not isinstance(session_id, str) or not session_id:
        raise InvalidCredentials()

    if user_id is None:
        raise InvalidCredentials()

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise InvalidCredentials() from None

    await get_validated_session(user_id, session_id)
    await refresh_session_activity(user_id, session_id)

    user = await get_user_by_id(
        user_repository,
        user_id,
    )

    if user is None or not user.is_active:
        raise InvalidCredentials()

    return AuthContext(
        user=user,
        session_id=session_id,
        token_jti=jti,
        token_exp=exp,
    )


CurrentUser = Annotated[AuthContext, Depends(get_current_user)]
