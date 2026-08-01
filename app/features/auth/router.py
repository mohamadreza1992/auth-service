from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.features.auth.dependencies import get_current_user
from app.features.auth.schemas import (
    RefreshTokenRequest,
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.features.auth.service import login_user, refresh_access_token, register_user

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    return await register_user(
        db,
        user_data,
    )


@router.post(
    "/login",
    response_model=Token,
)
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    return await login_user(
        db,
        user_data,
    )


@router.get("/me", response_model=UserResponse)
async def me(
    current_user=Depends(get_current_user),
):
    return current_user


@router.post("/logout")
async def logout(
    current_user=Depends(get_current_user),
):
    return {
        "message": "Successfully logged out",
    }


@router.post("/refresh", response_model=Token)
async def refresh(data: RefreshTokenRequest):
    return await refresh_access_token(data)
