from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.features.auth.models import User
from app.features.auth.repository import (
    create_user,
    get_user_by_email,
)
from app.features.auth.schemas import UserCreate


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
