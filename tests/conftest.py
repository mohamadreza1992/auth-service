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
    create_async_engine,
)

from app.core.config import settings
from app.database.session import get_db
from app.main import app


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, redis_client: Redis):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def test_settings():
    return settings


@pytest_asyncio.fixture
async def db_engine() -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine(settings.database_url, echo=False)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def redis_client(monkeypatch) -> AsyncGenerator[Redis]:
    client = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )

    monkeypatch.setattr(
        "app.features.sessions.session_store.redis_client",
        client,
    )

    monkeypatch.setattr(
        "app.core.token_blacklist.redis_client",
        client,
    )

    try:
        yield client
    finally:
        await client.flushdb()
        await client.aclose()


@pytest_asyncio.fixture
async def db_session(
    db_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession]:
    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await transaction.rollback()
            await session.close()
