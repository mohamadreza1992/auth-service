from datetime import UTC, datetime
from uuid import uuid4

from pydantic import IPvAnyAddress

from app.features.sessions.schemas import Session
from app.features.sessions.session_store import (
    delete_all_sessions,
    delete_session,
    get_session,
    save_session,
    touch_session,
)


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
    session = await get_session(user_id, session_id)
    return session


async def revoke_session(user_id: int, session_id: str):
    await delete_session(user_id, session_id)


async def revoke_all_sessions(user_id: int):
    await delete_all_sessions(user_id)


async def refresh_session_activity(user_id: int, session_id: str):
    await touch_session(user_id, session_id)
