import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.core.token_blacklist import blacklist_token
from app.core.token_store import (
    delete_all_refresh_tokens,
    delete_refresh_token,
    get_refresh_token,
    save_refresh_token,
)
from app.features.auth.models import User
from app.features.auth.repository import (
    create_user,
    get_user_by_email,
)
from app.features.auth.schemas import RefreshTokenRequest, Token, UserCreate, UserLogin


async def register_user(
    db: AsyncSession,
    user_data: UserCreate,
) -> User:
    existing_user = await get_user_by_email(
        db,
        user_data.email,
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not verify_password(
        user_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    session_id = str(uuid.uuid4())

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "session_id": session_id},
    )

    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "email": user.email, "session_id": session_id},
    )
    await save_refresh_token(
        user_id=user.id,
        session_id=session_id,
        token=refresh_token,
        expire_seconds=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from None

    user_id = payload.get("sub")
    email = payload.get("email")
    session_id = payload.get("session_id")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    if session_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    stored_token = await get_refresh_token(int(user_id), session_id)

    if stored_token != data.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    await delete_refresh_token(int(user_id), session_id)

    access_token = create_access_token(
        data={
            "sub": user_id,
            "email": email,
            "session_id": session_id,
        }
    )
    new_refresh_token = create_refresh_token(
        data={
            "sub": user_id,
            "email": email,
            "session_id": session_id,
        }
    )
    await save_refresh_token(
        user_id=int(user_id),
        session_id=session_id,
        token=new_refresh_token,
        expire_seconds=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
    )

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


async def logout_user(user_id: int, session_id: str, token_jti: str, token_exp: int):
    await delete_refresh_token(
        user_id,
        session_id,
    )
    print("USER ID:", user_id)
    print("SESSION ID:", session_id)

    remaining_time = token_exp - int(datetime.now(UTC).timestamp())

    if remaining_time > 0:
        await blacklist_token(
            token_jti,
            remaining_time,
        )

    return {"message": "Successfully logged out"}


async def logout_all_users(user_id: int):
    await delete_all_refresh_tokens(user_id)

    return {
        "message": "Successfully logged out from all devices",
    }
