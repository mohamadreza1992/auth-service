import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.features.sessions import session_store
from app.features.sessions.schemas import Session


@pytest.mark.asyncio
async def test_touch_session_does_not_overwrite_rotated_jti(redis_client):
    user_id = 123
    session_id = uuid4()

    now = datetime.now(UTC)

    session = Session(
        user_id=user_id,
        session_id=session_id,
        jti="A",
        created_at=now,
        last_used_at=now,
    )

    await session_store.save_session(
        session,
        expire_seconds=300,
    )

    touch_ready = asyncio.Event()
    continue_touch = asyncio.Event()

    original_pipeline = redis_client.pipeline
    pipeline_count = 0

    def controlled_pipeline(*args, **kwargs):
        nonlocal pipeline_count

        pipeline_count += 1
        pipe = original_pipeline(*args, **kwargs)

        if pipeline_count == 1:
            original_execute = pipe.execute

            async def controlled_execute(*args, **kwargs):
                touch_ready.set()

                await asyncio.wait_for(
                    continue_touch.wait(),
                    timeout=2,
                )

                return await original_execute(*args, **kwargs)

            pipe.execute = controlled_execute

        return pipe

    redis_client.pipeline = controlled_pipeline

    try:
        touch_task = asyncio.create_task(
            session_store.touch_session(
                user_id,
                str(session_id),
            )
        )

        await asyncio.wait_for(
            touch_ready.wait(),
            timeout=2,
        )

        result = await session_store.update_session_jti(
            user_id=user_id,
            session_id=str(session_id),
            expected_jti="A",
            new_jti="B",
        )

        assert result is True

        continue_touch.set()

        await touch_task

    finally:
        redis_client.pipeline = original_pipeline

    final_session = await session_store.get_session(
        user_id,
        str(session_id),
    )

    assert final_session is not None
    assert final_session.jti == "B"


@pytest.mark.asyncio
async def test_touch_session_does_not_resurrect_deleted_session(redis_client):
    user_id = 123
    session_id = uuid4()
    key = f"session:{user_id}:{session_id}"

    now = datetime.now(UTC)

    session = Session(
        user_id=user_id,
        session_id=session_id,
        jti="A",
        created_at=now,
        last_used_at=now,
    )

    await session_store.save_session(
        session,
        expire_seconds=300,
    )

    touch_ready = asyncio.Event()
    continue_touch = asyncio.Event()

    original_pipeline = redis_client.pipeline
    pipeline_count = 0

    def controlled_pipeline(*args, **kwargs):
        nonlocal pipeline_count

        pipeline_count += 1
        pipe = original_pipeline(*args, **kwargs)

        if pipeline_count == 1:
            original_execute = pipe.execute

            async def controlled_execute(*args, **kwargs):
                touch_ready.set()

                await asyncio.wait_for(
                    continue_touch.wait(),
                    timeout=2,
                )

                return await original_execute(*args, **kwargs)

            pipe.execute = controlled_execute

        return pipe

    redis_client.pipeline = controlled_pipeline

    try:
        touch_task = asyncio.create_task(
            session_store.touch_session(
                user_id,
                str(session_id),
            )
        )

        await asyncio.wait_for(
            touch_ready.wait(),
            timeout=2,
        )

        await session_store.delete_session(
            user_id,
            str(session_id),
        )

        assert await redis_client.exists(key) == 0

        continue_touch.set()

        await touch_task

    finally:
        redis_client.pipeline = original_pipeline

    final_session = await session_store.get_session(
        user_id,
        str(session_id),
    )

    assert final_session is None
    assert await redis_client.exists(key) == 0
    assert await redis_client.ttl(key) == -2


@pytest.mark.asyncio
async def test_touch_session_preserves_ttl(redis_client):
    user_id = 123
    session_id = uuid4()
    key = f"session:{user_id}:{session_id}"

    now = datetime.now(UTC)

    session = Session(
        user_id=user_id,
        session_id=session_id,
        jti="A",
        created_at=now,
        last_used_at=now,
    )

    await session_store.save_session(
        session,
        expire_seconds=300,
    )

    ttl_before = await redis_client.ttl(key)

    assert 0 < ttl_before <= 300

    await session_store.touch_session(
        user_id,
        str(session_id),
    )

    ttl_after = await redis_client.ttl(key)

    assert 0 < ttl_after <= ttl_before
