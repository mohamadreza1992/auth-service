from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.features.auth.schemas import UserCreate, UserResponse
from app.features.auth.service import register_user

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
