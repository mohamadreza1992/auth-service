from datetime import UTC, datetime
from uuid import uuid4

from pydantic import IPvAnyAddress

from app.core.exceptions import SessionOperationInProgress
from app.features.sessions.lock import (
    acquire_session_lock,
    release_session_lock,
)
from app.features.sessions.schemas import Session, SessionResponse
from app.features.sessions.session_store import (
    delete_all_sessions,
    delete_session,
    get_all_sessions,
    save_session,
    touch_session,
    update_session_jti,
)
from app.features.sessions.session_validation import validate_session


async def create_session(
    user_id: int,
    jti: str,
    device: str | None,
    ip_address: IPvAnyAddress | None,
    expire_seconds: int,
):
    session_id = uuid4()
    now = datetime.now(UTC)
    created_at = now
    last_used_at = now
    session = Session(
        session_id=session_id,
        user_id=user_id,
        jti=jti,
        device=device,
        ip_address=ip_address,
        created_at=created_at,
        last_used_at=last_used_at,
    )

    await save_session(session, expire_seconds)
    return session


async def fetch_session(user_id: int, session_id: str):
    session = await validate_session(user_id, session_id)
    response = SessionResponse(
        session_id=session.session_id,
        device=session.device,
        ip_address=session.ip_address,
        created_at=session.created_at,
        last_used_at=session.last_used_at,
    )

    return response


async def revoke_session(user_id: int, session_id: str):
    await delete_session(user_id, session_id)


async def revoke_all_sessions(user_id: int):
    lock_token = await acquire_session_lock(user_id)

    if lock_token is None:
        raise SessionOperationInProgress()

    try:
        await delete_all_sessions(user_id)
    finally:
        await release_session_lock(
            user_id,
            lock_token,
        )


async def refresh_session_activity(user_id: int, session_id: str):
    await touch_session(user_id, session_id)


async def rotate_session_jti(
    user_id: int,
    session_id: str,
    expected_jti: str,
    new_jti: str,
) -> bool:
    return await update_session_jti(
        user_id,
        session_id,
        expected_jti,
        new_jti,
    )


async def list_user_sessions(user_id: int) -> list[SessionResponse]:
    sessions = await get_all_sessions(user_id)
    responses = []

    for session in sessions:
        response = SessionResponse(
            session_id=session.session_id,
            device=session.device,
            ip_address=session.ip_address,
            created_at=session.created_at,
            last_used_at=session.last_used_at,
        )
        responses.append(response)
    return responses
