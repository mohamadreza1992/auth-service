from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.users.models import UserProfile


class UserProfileRepository(Protocol):
    async def get_by_user_id(
        self,
        user_id: int,
    ) -> UserProfile | None: ...
    async def update(self, user_id: int, data: dict) -> UserProfile | None: ...


class SQLAlchemyUserProfileRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user_id(self, user_id: int) -> UserProfile | None:
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )

        return result.scalar_one_or_none()

    async def update(
        self,
        user_id: int,
        data: dict[str, str | None],
    ) -> UserProfile | None:
        profile = await self.get_by_user_id(user_id)

        if profile is None:
            return None

        if "first_name" in data:
            profile.first_name = data["first_name"]

        if "last_name" in data:
            profile.last_name = data["last_name"]

        if "avatar_url" in data:
            profile.avatar_url = data["avatar_url"]

        await self.db.commit()
        await self.db.refresh(profile)

        return profile
