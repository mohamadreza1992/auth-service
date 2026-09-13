from datetime import UTC, datetime

from app.core.redis_client import redis_client
from app.features.sessions.schemas import Session


async def save_session(session: Session, expire_seconds: int) -> None:
    key = f"session:{session.user_id}:{session.session_id}"
    await redis_client.set(key, session.model_dump_json(), ex=expire_seconds)


async def get_session(user_id: int, session_id: str) -> Session | None:
    key = f"session:{user_id}:{session_id}"
    data = await redis_client.get(key)

    if data is None:
        return None
    return Session.model_validate_json(data)


async def delete_session(user_id: int, session_id: str) -> None:
    key = f"session:{user_id}:{session_id}"
    await redis_client.delete(key)


async def delete_all_sessions(user_id: int) -> None:
    pattern = f"session:{user_id}:*"
    async for key in redis_client.scan_iter(match=pattern):
        await redis_client.delete(key)


async def touch_session(user_id: int, session_id: str) -> None:
    key = f"session:{user_id}:{session_id}"
    data = await redis_client.get(key)
    if data is None:
        return
    session = Session.model_validate_json(data)
    session.last_used_at = datetime.now(UTC)

    await redis_client.set(key, session.model_dump_json(), keepttl=True)


async def update_session_jti(
    user_id: int,
    session_id: str,
    jti: str,
) -> None:
    key = f"session:{user_id}:{session_id}"
    data = await redis_client.get(key)
    if data is None:
        return
    session = Session.model_validate_json(data)
    session.jti = jti

    await redis_client.set(key, session.model_dump_json(), keepttl=True)
