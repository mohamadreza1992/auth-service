from typing import Protocol

from app.features.sessions.entities import Session


class SessionRepository(Protocol):
    async def save(self, session: Session, expire_seconds: int) -> None: ...

    async def get(self, user_id: int, session_id: str) -> Session | None: ...

    async def delete(self, user_id: int, session_id: str) -> None: ...

    async def delete_all(self, user_id: int) -> None: ...

    async def touch(self, user_id: int, session_id: str) -> None: ...

    async def get_all(self, user_id: int) -> list[Session]: ...

    async def update_jti(
        self,
        *,
        user_id: int,
        session_id: str,
        expected_jti: str,
        new_jti: str,
    ) -> bool: ...


class SessionLockManager(Protocol):
    async def acquire(self, user_id: int) -> str | None: ...

    async def release(
        self,
        user_id: int,
        token: str,
    ) -> bool: ...
