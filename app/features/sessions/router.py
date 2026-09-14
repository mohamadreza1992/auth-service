from fastapi import APIRouter, Depends

from app.features.auth.dependencies import get_current_user
from app.features.sessions.schemas import SessionResponse
from app.features.sessions.service import (
    fetch_session,
    list_user_sessions,
    revoke_all_sessions,
    revoke_session,
)

router = APIRouter(
    prefix="/sessions",
    tags=["sessions"],
)


@router.get("/", response_model=list[SessionResponse])
async def get_my_sessions(
    auth=Depends(get_current_user),
):
    return await list_user_sessions(auth.user.id)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, auth=Depends(get_current_user)):
    return await fetch_session(auth.user.id, session_id)


@router.delete("/{session_id}", status_code=204)
async def delete_my_session(session_id: str, auth=Depends(get_current_user)):
    await revoke_session(auth.user.id, session_id)


@router.delete("/", status_code=204)
async def delete_all_my_sessions(
    auth=Depends(get_current_user),
):
    await revoke_all_sessions(auth.user.id)
