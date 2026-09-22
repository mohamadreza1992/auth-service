from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.users.models import UserProfile


class UserProfileRepository(Protocol):
    async def get_by_user_id(
        self,
        user_id: int,
    ) -> UserProfile | None: ...


class SQLAlchemyUserProfileRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user_id(self, user_id: int) -> UserProfile | None:
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )

        return result.scalar_one_or_none()
