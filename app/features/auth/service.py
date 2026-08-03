from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.core.token_store import (
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

    return await create_user(
        db,
        user,
    )


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

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "email": user.email},
    )
    await save_refresh_token(
        user_id=user.id,
        token=refresh_token,
        expire_seconds=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
    )
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


async def refresh_access_token(data: RefreshTokenRequest):
    payload = decode_refresh_token(data.refresh_token)

    user_id = payload.get("sub")
    email = payload.get("email")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    stored_token = await get_refresh_token(int(user_id))

    if stored_token != data.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    access_token = create_access_token(
        data={
            "sub": user_id,
            "email": email,
        }
    )

    return Token(
        access_token=access_token,
        refresh_token=data.refresh_token,
        token_type="bearer",
    )


async def logout_user(user_id: int):
    await delete_refresh_token(user_id)

    return {"message": "Successfully logged out"}
