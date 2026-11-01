from datetime import UTC, datetime
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import WatchError

from app.core.redis_client import redis_client
from app.features.sessions.entities import Session


class RedisSessionRepository:
    def __init__(self, redis: Redis | None = None) -> None:
        self._redis = redis

    @property
    def redis(self) -> Redis:
        if self._redis is not None:
            return self._redis
        import app.features.sessions.session_store as store_mod

        return getattr(store_mod, "redis_client", redis_client)

    @staticmethod
    def _make_key(user_id: int, session_id: str | UUID) -> str:
        return f"session:{user_id}:{session_id}"

    async def save(self, session: Session, expire_seconds: int) -> None:
        key = self._make_key(session.user_id, session.session_id)
        await self.redis.set(key, session.model_dump_json(), ex=expire_seconds)

    async def get(self, user_id: int, session_id: str) -> Session | None:
        key = self._make_key(user_id, session_id)
        data = await self.redis.get(key)

        if data is None:
            return None
        return Session.model_validate_json(data)

    async def delete(self, user_id: int, session_id: str) -> None:
        key = self._make_key(user_id, session_id)
        await self.redis.delete(key)

    async def delete_all(self, user_id: int) -> None:
        pattern = f"session:{user_id}:*"
        async for key in self.redis.scan_iter(match=pattern):
            await self.redis.delete(key)

    async def touch(self, user_id: int, session_id: str) -> None:
        key = self._make_key(user_id, session_id)

        async with self.redis.pipeline(transaction=True) as pipe:
            try:
                await pipe.watch(key)
                data = await pipe.get(key)

                if data is None:
                    await pipe.unwatch()
                    return

                session = Session.model_validate_json(data)
                session.last_used_at = datetime.now(UTC)

                pipe.multi()
                pipe.set(
                    key,
                    session.model_dump_json(),
                    keepttl=True,
                )
                await pipe.execute()

            except WatchError:
                return

    async def get_all(self, user_id: int) -> list[Session]:
        pattern = f"session:{user_id}:*"
        sessions: list[Session] = []

        async for key in self.redis.scan_iter(match=pattern):
            data = await self.redis.get(key)

            if data is None:
                continue

            sessions.append(Session.model_validate_json(data))

        return sessions

    async def update_jti(
        self,
        *,
        user_id: int,
        session_id: str,
        expected_jti: str,
        new_jti: str,
    ) -> bool:
        key = self._make_key(user_id, session_id)

        async with self.redis.pipeline(transaction=True) as pipe:
            try:
                await pipe.watch(key)
                data = await pipe.get(key)

                if data is None:
                    await pipe.unwatch()
                    return False

                session = Session.model_validate_json(data)

                if session.jti != expected_jti:
                    await pipe.unwatch()
                    return False

                session.jti = new_jti

                pipe.multi()
                pipe.set(
                    key,
                    session.model_dump_json(),
                    keepttl=True,
                )

                result = await pipe.execute()
                return result is not None

            except WatchError:
                return False


_default_store = RedisSessionRepository()

save_session = _default_store.save
get_session = _default_store.get
delete_session = _default_store.delete
delete_all_sessions = _default_store.delete_all
touch_session = _default_store.touch
get_all_sessions = _default_store.get_all


async def update_session_jti(
    user_id: int,
    session_id: str,
    expected_jti: str,
    new_jti: str,
) -> bool:
    return await _default_store.update_jti(
        user_id=user_id,
        session_id=session_id,
        expected_jti=expected_jti,
        new_jti=new_jti,
    )
