from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ProfileNotFound
from app.features.users.models import User, UserProfile
from app.features.users.repository import (
    UserProfileRepository,
)
from app.features.users.repository import (
    create_user as repository_create_user,
)
from app.features.users.repository import (
    create_user_profile as repository_create_user_profile,
)
from app.features.users.repository import (
    get_user_by_email as repository_get_user_by_email,
)
from app.features.users.repository import (
    get_user_by_id as repository_get_user_by_id,
)


async def get_profile(repository: UserProfileRepository, user_id: int) -> UserProfile:
    profile = await repository.get_by_user_id(user_id)
    if profile is None:
        raise ProfileNotFound()
    return profile


async def update_profile(
    db: AsyncSession,
    repository: UserProfileRepository,
    user_id: int,
    fields: dict[str, Any],
) -> UserProfile:
    # PATCH semantics: `fields` holds only what the client sent.
    # A missing key means "leave unchanged"; a key with None means "set to null".
    try:
        profile = await repository.update(user_id, fields)

        if profile is None:
            raise ProfileNotFound()

        await db.commit()
        return profile

    except Exception:
        await db.rollback()
        raise


async def replace_profile(
    db: AsyncSession,
    repository: UserProfileRepository,
    user_id: int,
    *,
    first_name: str,
    last_name: str,
    avatar_url: str,
) -> UserProfile:
    try:
        profile = await repository.update(
            user_id,
            {
                "first_name": first_name,
                "last_name": last_name,
                "avatar_url": avatar_url,
            },
        )

        if profile is None:
            raise ProfileNotFound()

        await db.commit()
        return profile

    except Exception:
        await db.rollback()
        raise


async def get_user_by_id(
    db: AsyncSession,
    user_id: int,
) -> User | None:
    return await repository_get_user_by_id(db, user_id)


async def get_user_by_email(
    db: AsyncSession,
    email: str,
) -> User | None:
    return await repository_get_user_by_email(db, email)


async def create_user(
    db: AsyncSession,
    user: User,
) -> User:
    return await repository_create_user(db, user)


async def create_profile(
    db: AsyncSession,
    profile: UserProfile,
) -> UserProfile:
    return await repository_create_user_profile(db, profile)
