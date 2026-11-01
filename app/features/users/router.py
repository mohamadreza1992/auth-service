from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.current_user import AuthContext, get_current_user
from app.features.users.dependencies import UserProfileRepoDep
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

CurrentUser = Annotated[AuthContext, Depends(get_current_user)]


@router.get("/profile", response_model=UserProfileResponse)
async def get_my_profile(
    auth: CurrentUser,
    repository: UserProfileRepoDep,
):
    return await get_profile(repository, auth.user.id)


@router.patch("/profile", response_model=UserProfileResponse)
async def update_my_profile(
    data: ProfileUpdate,
    auth: CurrentUser,
    repository: UserProfileRepoDep,
):
    return await update_profile(
        repository,
        auth.user.id,
        data.model_dump(mode="json", exclude_unset=True),
    )


@router.put("/profile", response_model=UserProfileResponse)
async def update_complete_profile(
    data: ProfileReplace,
    auth: CurrentUser,
    repository: UserProfileRepoDep,
):
    return await replace_profile(
        repository,
        auth.user.id,
        first_name=data.first_name,
        last_name=data.last_name,
        avatar_url=str(data.avatar_url) if data.avatar_url is not None else None,
    )
