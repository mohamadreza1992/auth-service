from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from ipaddress import IPv4Address, IPv6Address
from uuid import uuid4

from app.core.exceptions import InvalidSession, SessionOperationInProgress
from app.features.sessions.entities import Session
from app.features.sessions.lock import (
    acquire_session_lock,
    release_session_lock,
)
from app.features.sessions.ports import SessionLockManager, SessionRepository
from app.features.sessions.session_store import (
    delete_all_sessions,
    delete_session,
    get_all_sessions,
    save_session,
    touch_session,
    update_session_jti,
)
from app.features.sessions.session_validation import validate_session


async def run_with_session_lock[T](
    user_id: int,
    operation: Callable[[], Awaitable[T]],
    lock_manager: SessionLockManager | None = None,
) -> T:
    if lock_manager is not None:
        lock_token = await lock_manager.acquire(user_id)
        if lock_token is None:
            raise SessionOperationInProgress()
        try:
            return await operation()
        finally:
            await lock_manager.release(user_id, lock_token)
    else:
        lock_token = await acquire_session_lock(user_id)
        if lock_token is None:
            raise SessionOperationInProgress()
        try:
            return await operation()
        finally:
            await release_session_lock(user_id, lock_token)


async def create_session(
    user_id: int,
    jti: str,
    device: str | None,
    ip_address: IPv4Address | IPv6Address | None,
    expire_seconds: int,
    repository: SessionRepository | None = None,
) -> Session:
    now = datetime.now(UTC)
    session = Session(
        session_id=uuid4(),
        user_id=user_id,
        jti=jti,
        device=device,
        ip_address=ip_address,
        created_at=now,
        last_used_at=now,
    )

    if repository is not None:
        await repository.save(session, expire_seconds)
    else:
        await save_session(session, expire_seconds)
    return session


async def get_validated_session(
    user_id: int,
    session_id: str,
    repository: SessionRepository | None = None,
) -> Session:
    if repository is not None:
        session = await repository.get(user_id, session_id)
        if session is None or session.user_id != user_id:
            raise InvalidSession()
        return session
    else:
        return await validate_session(user_id, session_id)


async def revoke_session(
    user_id: int,
    session_id: str,
    repository: SessionRepository | None = None,
) -> None:
    if repository is not None:
        await repository.delete(user_id, session_id)
    else:
        await delete_session(user_id, session_id)


async def revoke_all_sessions(
    user_id: int,
    repository: SessionRepository | None = None,
    lock_manager: SessionLockManager | None = None,
) -> None:
    if repository is not None or lock_manager is not None:
        from app.features.sessions.dependencies import (
            get_session_lock_manager,
            get_session_repository,
        )

        repo = repository or get_session_repository()
        lock = lock_manager or get_session_lock_manager()
        await run_with_session_lock(
            user_id,
            lambda: repo.delete_all(user_id),
            lock_manager=lock,
        )
    else:
        lock_token = await acquire_session_lock(user_id)
        if lock_token is None:
            raise SessionOperationInProgress()
        try:
            await delete_all_sessions(user_id)
        finally:
            await release_session_lock(user_id, lock_token)


async def refresh_session_activity(
    user_id: int,
    session_id: str,
    repository: SessionRepository | None = None,
) -> None:
    if repository is not None:
        await repository.touch(user_id, session_id)
    else:
        await touch_session(user_id, session_id)


async def rotate_session_jti(
    user_id: int,
    session_id: str,
    expected_jti: str,
    new_jti: str,
    repository: SessionRepository | None = None,
) -> bool:
    if repository is not None:
        return await repository.update_jti(
            user_id=user_id,
            session_id=session_id,
            expected_jti=expected_jti,
            new_jti=new_jti,
        )
    else:
        return await update_session_jti(
            user_id,
            session_id,
            expected_jti,
            new_jti,
        )


async def list_user_sessions(
    user_id: int,
    repository: SessionRepository | None = None,
) -> list[Session]:
    if repository is not None:
        return await repository.get_all(user_id)
    else:
        return await get_all_sessions(user_id)
