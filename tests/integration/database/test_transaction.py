import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models import User


@pytest.mark.asyncio
async def test_user_01_is_rolled_back_after_test(
    db_session: AsyncSession,
):
    user = User(
        email="isolation@example.com",
        password_hash="hashed-password",
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()


@pytest.mark.asyncio
async def test_user_02_from_previous_test_does_not_exist(
    db_session: AsyncSession,
):
    result = await db_session.execute(
        select(User).where(User.email == "isolation@example.com")
    )

    user = result.scalar_one_or_none()

    assert user is None
