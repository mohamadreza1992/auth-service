from app.features.users.models import UserProfile
from app.features.users.repository import UserProfileRepository


async def get_profile(
    repository: UserProfileRepository, user_id: int
) -> UserProfile | None:
    return await repository.get_by_user_id(user_id)
