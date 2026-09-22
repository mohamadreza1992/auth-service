from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.features.users.repository import SQLAlchemyUserProfileRepository


async def get_user_profile_repository(
    db: AsyncSession = Depends(get_db),
) -> SQLAlchemyUserProfileRepository:
    return SQLAlchemyUserProfileRepository(db)
