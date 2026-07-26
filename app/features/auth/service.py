from sqlalchemy.ext.asyncio import AsyncSession

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
        raise ValueError("Email already registered")

    user = User(
        email=user_data.email,
        password_hash=user_data.password,
        is_active=True,
    )

    return await create_user(
        db,
        user,
    )
