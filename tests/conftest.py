import os

os.environ["APP_ENV"] = "test"

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx2 import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.main import app


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def test_settings():
    return settings


@pytest_asyncio.fixture
async def db_engine() -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine(settings.database_url, echo=False)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def redis_client() -> AsyncGenerator[Redis]:
    client = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )

    yield client

    await client.aclose()


@pytest_asyncio.fixture
async def db_session(
    db_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession]:

    session_factory = async_sessionmaker(
        bind=db_engine,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session
