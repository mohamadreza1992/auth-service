from fastapi import APIRouter

from app.dependencies.current_user import CurrentUser
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
from app.features.users.dependencies import UserRepoDep

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
    user_repository: UserRepoDep,
):
    return await register_user(
        user_repository,
        email=user_data.email,
        password=user_data.password,
    )


@router.post(
    "/login",
    response_model=Token,
)
async def login(
    user_data: UserLogin,
    user_repository: UserRepoDep,
):
    pair = await login_user(
        user_repository,
        email=user_data.email,
        password=user_data.password,
    )
    return to_token(pair)


@router.get("/me", response_model=UserResponse)
async def me(auth: CurrentUser):
    return auth.user


@router.post("/logout")
async def logout(auth: CurrentUser):
    await logout_user(
        user_id=auth.user.id,
        session_id=auth.session_id,
        token_jti=auth.token_jti,
        token_exp=auth.token_exp,
    )
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=Token)
async def refresh(
    data: RefreshTokenRequest,
    user_repository: UserRepoDep,
):
    pair = await refresh_access_token(
        user_repository,
        refresh_token=data.refresh_token,
    )
    return to_token(pair)


@router.post("/logout-all")
async def logout_all(auth: CurrentUser):
    await logout_all_users(auth.user.id)
    return {"message": "Successfully logged out from all devices"}
