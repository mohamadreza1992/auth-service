from app.core.exceptions import ProfileNotFound
from app.features.users.models import UserProfile
from app.features.users.repository import UserProfileRepository
from app.features.users.schemas import ProfileReplace, ProfileUpdate


async def get_profile(repository: UserProfileRepository, user_id: int) -> UserProfile:
    profile = await repository.get_by_user_id(user_id)
    if profile is None:
        raise ProfileNotFound()
    return profile


async def update_profile(
    repository: UserProfileRepository,
    user_id: int,
    data: ProfileUpdate,
) -> UserProfile:
    update_data = data.model_dump(exclude_unset=True)
    profile = await repository.update(user_id, update_data)
    if profile is None:
        raise ProfileNotFound()

    return profile


async def replace_profile(
    repository: UserProfileRepository,
    user_id: int,
    data: ProfileReplace,
) -> UserProfile:
    profile = await repository.update(
        user_id,
        {
            "first_name": data.first_name,
            "last_name": data.last_name,
            "avatar_url": data.avatar_url,
        },
    )

    if profile is None:
        raise ProfileNotFound()

    return profile
