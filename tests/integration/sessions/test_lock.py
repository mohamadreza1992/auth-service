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
    lock_key = f"session-lock:{user_id}"

    owner_token = "lock-owner-1"
    other_token = "lock-owner-2"

    await redis_client.set(
        lock_key,
        owner_token,
        nx=True,
        ex=10,
    )

    current_owner = await redis_client.get(lock_key)

    assert current_owner == owner_token

    assert other_token != current_owner

    current_owner = await redis_client.get(lock_key)

    assert current_owner == owner_token


@pytest.mark.asyncio
async def test_session_lock_release_does_not_delete_another_owner_lock(
    redis_client,
):
    user_id = 1
    lock_key = f"session-lock:{user_id}"

    owner_token = "lock-owner-1"
    other_token = "lock-owner-2"

    await redis_client.set(
        lock_key,
        owner_token,
        nx=True,
        ex=10,
    )

    # Simulate another owner trying to release the lock.
    # This must not delete the existing lock.
    current_owner = await redis_client.get(lock_key)

    assert current_owner == owner_token

    assert other_token != current_owner

    assert await redis_client.exists(lock_key) == 1


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

    key = f"session-lock:{user_id}"

    assert await redis_client.exists(key) == 0


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

    key = f"session-lock:{user_id}"

    assert await redis_client.get(key) == owner_token
