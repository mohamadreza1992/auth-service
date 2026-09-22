from fastapi import APIRouter, Depends

from app.features.users.dependencies import get_user_profile_repository
from app.features.users.repository import UserProfileRepository
from app.features.users.service import get_profile

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.get("/profile")
async def get_my_profile(
    user_id: int,
    repository: UserProfileRepository = Depends(get_user_profile_repository),
):
    return await get_profile(repository, user_id)
