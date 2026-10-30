from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.current_user import get_current_user
from app.features.auth.schemas import (
    RefreshTokenRequest,
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.features.auth.service import (
    TokenPair,
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


def to_token(pair: TokenPair) -> Token:
    return Token(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        token_type="bearer",
    )


@router.post(
    "/register",
    response_model=UserResponse,
)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    return await register_user(db, email=user_data.email, password=user_data.password)


@router.post(
    "/login",
    response_model=Token,
)
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    pair = await login_user(
        db,
        email=user_data.email,
        password=user_data.password,
    )
    return to_token(pair)


@router.get("/me", response_model=UserResponse)
async def me(
    auth=Depends(get_current_user),
):
    return auth.user


@router.post("/logout")
async def logout(
    auth=Depends(get_current_user),
):
    await logout_user(
        user_id=auth.user.id,
        session_id=auth.session_id,
        token_jti=auth.token_jti,
        token_exp=auth.token_exp,
    )
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=Token)
async def refresh(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    pair = await refresh_access_token(db, refresh_token=data.refresh_token)
    return to_token(pair)


@router.post("/logout-all")
async def logout_all(auth=Depends(get_current_user)):
    await logout_all_users(auth.user.id)
    return {"message": "Successfully logged out from all devices"}
