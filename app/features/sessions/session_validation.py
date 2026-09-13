from app.core.exceptions import InvalidSession, InvalidToken
from app.features.sessions.schemas import Session
from app.features.sessions.session_store import get_session


async def validate_session(user_id: int, session_id: str):
    session = await get_session(user_id, session_id)
    if session is None:
        raise InvalidSession()
    return session


async def validate_session_jti(session: Session, jti: str):
    if session.jti != jti:
        raise InvalidToken()
    return session
