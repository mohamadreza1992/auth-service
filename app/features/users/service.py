from app.core.exceptions import ProfileNotFound
from app.features.users.entities import UserEntity, UserProfileEntity
from app.features.users.ports import (
    UserProfileRepository,
    UserRepository,
)


async def get_user_by_id(
    repository: UserRepository,
    user_id: int,
) -> UserEntity | None:
    return await repository.get_by_id(user_id)


async def get_user_by_email(
    repository: UserRepository,
    email: str,
) -> UserEntity | None:
    normalized_email = email.strip().lower()
    return await repository.get_by_email(normalized_email)


async def create_user_with_profile(
    repository: UserRepository,
    *,
    email: str,
    password_hash: str,
    is_active: bool = True,
) -> UserEntity:
    normalized_email = email.strip().lower()
    return await repository.create_with_profile(
        email=normalized_email,
        password_hash=password_hash,
        is_active=is_active,
    )


async def get_profile(
    repository: UserProfileRepository,
    user_id: int,
) -> UserProfileEntity:
    profile = await repository.get_by_user_id(user_id)
    if profile is None:
        raise ProfileNotFound()
    return profile


async def update_profile(
    repository: UserProfileRepository,
    user_id: int,
    data: dict[str, str | None],
) -> UserProfileEntity:
    profile = await repository.update(user_id, data)
    if profile is None:
        raise ProfileNotFound()
    return profile


async def replace_profile(
    repository: UserProfileRepository,
    user_id: int,
    *,
    first_name: str | None,
    last_name: str | None,
    avatar_url: str | None,
) -> UserProfileEntity:
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
    return profile
