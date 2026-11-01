from typing import Annotated

from fastapi import Depends

from app.features.sessions.lock import (
    RedisSessionLockManager,
)
from app.features.sessions.ports import SessionLockManager, SessionRepository
from app.features.sessions.session_store import (
    RedisSessionRepository,
)


def get_session_repository() -> SessionRepository:
    return RedisSessionRepository()


def get_session_lock_manager() -> SessionLockManager:
    return RedisSessionLockManager()


SessionRepoDep = Annotated[SessionRepository, Depends(get_session_repository)]
SessionLockDep = Annotated[SessionLockManager, Depends(get_session_lock_manager)]
