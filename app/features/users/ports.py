from typing import Protocol

from app.features.users.entities import UserEntity, UserProfileEntity


class UserRepository(Protocol):
    async def get_by_id(self, user_id: int) -> UserEntity | None: ...

    async def get_by_email(self, email: str) -> UserEntity | None: ...

    async def create(
        self,
        *,
        email: str,
        password_hash: str,
        is_active: bool = True,
    ) -> UserEntity: ...

    async def create_with_profile(
        self,
        *,
        email: str,
        password_hash: str,
        is_active: bool = True,
    ) -> UserEntity: ...


class UserProfileRepository(Protocol):
    async def get_by_user_id(self, user_id: int) -> UserProfileEntity | None: ...

    async def update(
        self,
        user_id: int,
        data: dict[str, str | None],
    ) -> UserProfileEntity | None: ...
