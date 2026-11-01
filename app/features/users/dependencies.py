from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.features.users.ports import (
    UserProfileRepository,
    UserRepository,
)
from app.features.users.repository import (
    SQLAlchemyUserProfileRepository,
    SQLAlchemyUserRepository,
)

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_user_repository(db: DbSession) -> UserRepository:
    return SQLAlchemyUserRepository(db)


def get_user_profile_repository(db: DbSession) -> UserProfileRepository:
    return SQLAlchemyUserProfileRepository(db)


UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]
UserProfileRepoDep = Annotated[
    UserProfileRepository, Depends(get_user_profile_repository)
]
