import pytest

from app.features.sessions.lock import (
    acquire_session_lock,
    release_session_lock,
)


@pytest.mark.asyncio
async def test_user_session_lock_cannot_be_acquired_twice(
    redis_client,
):
    user_id = 1

    lock_key = f"session-lock:{user_id}"

    first_lock = await redis_client.set(
        lock_key,
        "lock-1",
        nx=True,
        ex=10,
    )

    second_lock = await redis_client.set(
        lock_key,
        "lock-2",
        nx=True,
        ex=10,
    )

    assert first_lock is True
    assert second_lock is None


@pytest.mark.asyncio
async def test_session_lock_can_only_be_released_by_owner(
    redis_client,
):
    user_id = 1

    owner_token = await acquire_session_lock(user_id)

    assert owner_token is not None

    released = await release_session_lock(
        user_id,
        "wrong-token",
    )

    assert released is False

    lock_key = f"session-lock:{user_id}"

    assert await redis_client.get(lock_key) == owner_token


@pytest.mark.asyncio
async def test_session_lock_owner_can_release_lock(
    redis_client,
):
    user_id = 1

    token = await acquire_session_lock(user_id)

    assert token is not None

    released = await release_session_lock(
        user_id,
        token,
    )

    assert released is True

    lock_key = f"session-lock:{user_id}"

    assert await redis_client.exists(lock_key) == 0


@pytest.mark.asyncio
async def test_session_lock_non_owner_cannot_release_lock(
    redis_client,
):
    user_id = 1

    owner_token = await acquire_session_lock(user_id)

    assert owner_token is not None

    released = await release_session_lock(
        user_id,
        "wrong-token",
    )

    assert released is False

    lock_key = f"session-lock:{user_id}"

    assert await redis_client.get(lock_key) == owner_token
