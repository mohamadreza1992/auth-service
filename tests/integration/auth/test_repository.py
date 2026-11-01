import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.users.models import User
from app.features.users.repository import SQLAlchemyUserRepository


@pytest.fixture
def user_repo(db_session: AsyncSession) -> SQLAlchemyUserRepository:
    return SQLAlchemyUserRepository(db_session)


@pytest.mark.asyncio
async def test_existing_user_by_email(
    db_session: AsyncSession, user_repo: SQLAlchemyUserRepository
):
    user = User(
        email="example@gmail.com", password_hash="hashed_password", is_active=True
    )
    db_session.add(user)
    await db_session.commit()

    result = await user_repo.get_by_email(user.email)

    assert result is not None
    assert result.email == user.email


@pytest.mark.asyncio
async def test_non_existing_user_by_email(user_repo: SQLAlchemyUserRepository):
    result = await user_repo.get_by_email("not_found@example.com")
    assert result is None


@pytest.mark.asyncio
async def test_create_user(
    db_session: AsyncSession, user_repo: SQLAlchemyUserRepository
):
    created_user = await user_repo.create(
        email="example@gmail.com",
        password_hash="hashed_password",
        is_active=True,
    )
    await db_session.commit()

    assert created_user.id is not None
    assert created_user.email == "example@gmail.com"


@pytest.mark.asyncio
async def test_existing_get_by_id(
    db_session: AsyncSession, user_repo: SQLAlchemyUserRepository
):
    user = User(
        email="example@gmail.com", password_hash="hashed_password", is_active=True
    )
    db_session.add(user)
    await db_session.commit()

    result = await user_repo.get_by_id(user.id)

    assert result is not None
    assert result.id == user.id


@pytest.mark.asyncio
async def test_no_existint_by_id(user_repo: SQLAlchemyUserRepository):
    result = await user_repo.get_by_id(999999999)
    assert result is None
