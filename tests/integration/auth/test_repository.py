import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models import User
from app.features.auth.repository import create_user, get_user_by_email, get_user_by_id


@pytest.mark.asyncio
async def test_existing_user_by_email(db_session: AsyncSession):
    user = User(
        email="example@gmail.com", password_hash="hashed_password", is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    result = await get_user_by_email(db_session, user.email)
    assert result is not None
    assert result.email == user.email


@pytest.mark.asyncio
async def test_non_existing_user_by_email(db_session: AsyncSession):
    result = await get_user_by_email(db_session, "not_found@example.com")
    assert result is None


@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession):
    user = User(
        email="example@gmail.com", password_hash="hashed_password", is_active=True
    )
    created_user = await create_user(db_session, user)
    await db_session.commit()
    assert created_user.id is not None
    assert created_user.email == user.email


@pytest.mark.asyncio
async def test_existing_get_by_id(db_session: AsyncSession):
    user = User(
        email="example@gmail.com", password_hash="hashed_password", is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    result = await get_user_by_id(db_session, user.id)

    assert result is not None
    assert result.id == user.id


@pytest.mark.asyncio
async def test_no_existint_by_id(db_session: AsyncSession):
    result = await get_user_by_id(db_session, 999999999)
    assert result is None
