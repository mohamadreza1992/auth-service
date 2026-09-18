from uuid import uuid4

from app.core.redis_client import redis_client


async def acquire_session_lock(user_id: int) -> str | None:
    key = f"session-lock:{user_id}"
    token = str(uuid4())

    acquired = await redis_client.set(
        key,
        token,
        nx=True,
        ex=10,
    )

    if not acquired:
        return None

    return token


RELEASE_LOCK_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
end
return 0
"""


async def release_session_lock(
    user_id: int,
    token: str,
) -> bool:
    key = f"session-lock:{user_id}"

    result = await redis_client.eval(
        RELEASE_LOCK_SCRIPT,
        1,
        key,
        token,
    )

    return result == 1
