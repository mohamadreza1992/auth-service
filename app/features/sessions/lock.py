from uuid import uuid4

from redis.asyncio import Redis

from app.core.redis_client import redis_client

RELEASE_LOCK_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
end
return 0
"""


class RedisSessionLockManager:
    def __init__(self, redis: Redis | None = None, ttl_seconds: int = 10) -> None:
        self._redis = redis
        self.ttl_seconds = ttl_seconds

    @property
    def redis(self) -> Redis:
        if self._redis is not None:
            return self._redis
        import app.features.sessions.lock as lock_mod

        return getattr(lock_mod, "redis_client", redis_client)

    @staticmethod
    def _make_key(user_id: int) -> str:
        return f"session-lock:{user_id}"

    async def acquire(self, user_id: int) -> str | None:
        key = self._make_key(user_id)
        token = str(uuid4())

        acquired = await self.redis.set(
            key,
            token,
            nx=True,
            ex=self.ttl_seconds,
        )

        if not acquired:
            return None

        return token

    async def release(
        self,
        user_id: int,
        token: str,
    ) -> bool:
        key = self._make_key(user_id)

        result = await self.redis.eval(  # type: ignore[misc]
            RELEASE_LOCK_SCRIPT,
            1,
            key,
            token,
        )

        return result == 1


default_lock_manager = RedisSessionLockManager()


async def acquire_session_lock(user_id: int) -> str | None:
    return await default_lock_manager.acquire(user_id)


async def release_session_lock(user_id: int, token: str) -> bool:
    return await default_lock_manager.release(user_id, token)
