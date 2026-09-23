from fastapi import APIRouter, Depends

from app.features.auth.dependencies import AuthContext, get_current_user
from app.features.users.dependencies import get_user_profile_repository
from app.features.users.repository import UserProfileRepository
from app.features.users.schemas import UserProfileResponse
from app.features.users.service import get_profile

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.get("/profile", response_model=UserProfileResponse)
async def get_my_profile(
    auth: AuthContext = Depends(get_current_user),
    repository: UserProfileRepository = Depends(get_user_profile_repository),
):
    return await get_profile(repository, auth.user.id)
