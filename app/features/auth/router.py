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
from app.features.auth.service import (
    login_user,
    logout_all_users,
    logout_user,
    refresh_access_token,
    register_user,
)

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
    auth=Depends(get_current_user),
):
    return auth.user


@router.post("/logout")
async def logout(
    auth=Depends(get_current_user),
):
    return await logout_user(
        user_id=auth.user.id,
        session_id=auth.session_id,
        token_jti=auth.token_jti,
        token_exp=auth.token_exp,
    )


@router.post("/refresh", response_model=Token)
async def refresh(data: RefreshTokenRequest):
    return await refresh_access_token(data)


@router.post("/logout-all")
async def logout_all(auth=Depends(get_current_user)):
    return await logout_all_users(auth.user.id)
