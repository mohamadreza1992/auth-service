from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.users.entities import UserEntity, UserProfileEntity
from app.features.users.exceptions import UserAlreadyExists
from app.features.users.models import User, UserProfile


class SQLAlchemyUserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _to_entity(model: User) -> UserEntity:
        return UserEntity(
            id=model.id,
            email=model.email,
            password_hash=model.password_hash,
            is_active=model.is_active,
            created_at=getattr(model, "created_at", None),
        )

    async def get_by_id(self, user_id: int) -> UserEntity | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        return self._to_entity(user) if user else None

    async def get_by_email(self, email: str) -> UserEntity | None:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        return self._to_entity(user) if user else None

    async def create(
        self,
        *,
        email: str,
        password_hash: str,
        is_active: bool = True,
    ) -> UserEntity:
        return await self.create_with_profile(
            email=email,
            password_hash=password_hash,
            is_active=is_active,
        )

    async def create_with_profile(
        self,
        *,
        email: str,
        password_hash: str,
        is_active: bool = True,
    ) -> UserEntity:
        user = User(
            email=email,
            password_hash=password_hash,
            is_active=is_active,
        )
        self.db.add(user)
        try:
            await self.db.flush()
            profile = UserProfile(user_id=user.id)
            self.db.add(profile)
            await self.db.commit()
            return self._to_entity(user)
        except IntegrityError as exc:
            await self.db.rollback()
            raise UserAlreadyExists() from exc
        except Exception:
            await self.db.rollback()
            raise


class SQLAlchemyUserProfileRepository:
    _ALLOWED_FIELDS = {"first_name", "last_name", "avatar_url"}

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _to_entity(model: UserProfile) -> UserProfileEntity:
        return UserProfileEntity(
            user_id=model.user_id,
            first_name=model.first_name,
            last_name=model.last_name,
            avatar_url=model.avatar_url,
        )

    async def get_by_user_id(self, user_id: int) -> UserProfileEntity | None:
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        return self._to_entity(profile) if profile else None

    async def update(
        self,
        user_id: int,
        data: dict[str, str | None],
    ) -> UserProfileEntity | None:
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            return None

        for field, value in data.items():
            if field in self._ALLOWED_FIELDS:
                setattr(profile, field, value)

        try:
            await self.db.commit()
            return self._to_entity(profile)
        except Exception:
            await self.db.rollback()
            raise
