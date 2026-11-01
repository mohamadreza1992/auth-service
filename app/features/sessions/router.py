from fastapi import APIRouter

from app.dependencies.current_user import CurrentUser
from app.features.sessions.dependencies import SessionLockDep, SessionRepoDep
from app.features.sessions.entities import Session
from app.features.sessions.schemas import SessionResponse
from app.features.sessions.service import (
    get_validated_session,
    list_user_sessions,
    revoke_all_sessions,
    revoke_session,
)

router = APIRouter(
    prefix="/sessions",
    tags=["sessions"],
)


def to_session_response(session: Session) -> SessionResponse:

    return SessionResponse(
        session_id=session.session_id,
        device=session.device,
        ip_address=session.ip_address,
        created_at=session.created_at,
        last_used_at=session.last_used_at,
    )


@router.get("/", response_model=list[SessionResponse])
async def get_my_sessions(
    auth: CurrentUser,
    repository: SessionRepoDep,
):
    sessions = await list_user_sessions(auth.user.id, repository=repository)
    return [to_session_response(session) for session in sessions]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    auth: CurrentUser,
    repository: SessionRepoDep,
):
    session = await get_validated_session(
        auth.user.id,
        session_id,
        repository=repository,
    )
    return to_session_response(session)


@router.delete("/{session_id}", status_code=204)
async def delete_my_session(
    session_id: str,
    auth: CurrentUser,
    repository: SessionRepoDep,
):
    await revoke_session(
        auth.user.id,
        session_id,
        repository=repository,
    )


@router.delete("/", status_code=204)
async def delete_all_my_sessions(
    auth: CurrentUser,
    repository: SessionRepoDep,
    lock_manager: SessionLockDep,
):
    await revoke_all_sessions(
        auth.user.id,
        repository=repository,
        lock_manager=lock_manager,
    )
