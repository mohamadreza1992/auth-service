from fastapi import APIRouter, Depends

from app.dependencies.current_user import get_current_user
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
    # Field-by-field on purpose: Session also holds jti and user_id,
    # which must never reach the API response.
    return SessionResponse(
        session_id=session.session_id,
        device=session.device,
        ip_address=session.ip_address,
        created_at=session.created_at,
        last_used_at=session.last_used_at,
    )


@router.get("/", response_model=list[SessionResponse])
async def get_my_sessions(
    auth=Depends(get_current_user),
):
    sessions = await list_user_sessions(auth.user.id)
    return [to_session_response(session) for session in sessions]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, auth=Depends(get_current_user)):
    session = await get_validated_session(auth.user.id, session_id)
    return to_session_response(session)


@router.delete("/{session_id}", status_code=204)
async def delete_my_session(session_id: str, auth=Depends(get_current_user)):
    await revoke_session(auth.user.id, session_id)


@router.delete("/", status_code=204)
async def delete_all_my_sessions(
    auth=Depends(get_current_user),
):
    await revoke_all_sessions(auth.user.id)
