from app.core.exceptions import ProfileNotFound
from app.features.users.models import UserProfile
from app.features.users.repository import UserProfileRepository


async def get_profile(repository: UserProfileRepository, user_id: int) -> UserProfile:
    profile = await repository.get_by_user_id(user_id)
    if profile is None:
        raise ProfileNotFound()
    return profile
