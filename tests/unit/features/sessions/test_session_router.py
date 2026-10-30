from datetime import UTC, datetime
from ipaddress import IPv4Address
from uuid import uuid4

from app.features.sessions.entities import Session
from app.features.sessions.router import to_session_response
from app.features.sessions.schemas import SessionResponse


def make_session() -> Session:
    now = datetime.now(UTC)

    return Session(
        session_id=uuid4(),
        user_id=123,
        jti="test-jti",
        device="Chrome",
        ip_address=IPv4Address("127.0.0.1"),
        created_at=now,
        last_used_at=now,
    )


def test_to_session_response_maps_public_fields():
    session = make_session()

    result = to_session_response(session)

    assert isinstance(result, SessionResponse)
    assert result.session_id == session.session_id
    assert result.device == session.device
    assert result.ip_address == session.ip_address
    assert result.created_at == session.created_at
    assert result.last_used_at == session.last_used_at


def test_to_session_response_does_not_expose_internal_fields():
    result = to_session_response(make_session())

    dumped = result.model_dump()

    assert "jti" not in dumped
    assert "user_id" not in dumped
