from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.current_user import AuthContext, get_current_user
from app.features.users.dependencies import get_user_profile_repository
from app.features.users.repository import UserProfileRepository
from app.features.users.schemas import (
    ProfileReplace,
    ProfileUpdate,
    UserProfileResponse,
)
from app.features.users.service import get_profile, replace_profile, update_profile

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


@router.patch("/profile", response_model=UserProfileResponse)
async def update_my_profile(
    data: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
    repository: UserProfileRepository = Depends(get_user_profile_repository),
):
    return await update_profile(
        db,
        repository,
        auth.user.id,
        data,
    )


@router.put("/profile", response_model=UserProfileResponse)
async def update_complete_profile(
    data: ProfileReplace,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
    repository: UserProfileRepository = Depends(get_user_profile_repository),
):
    return await replace_profile(
        db,
        repository,
        auth.user.id,
        data,
    )
