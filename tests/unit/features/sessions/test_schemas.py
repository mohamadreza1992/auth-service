from datetime import UTC, datetime
from ipaddress import IPv4Address
from uuid import uuid4

import pytest

from app.features.sessions.schemas import Session, SessionCreate, SessionResponse


def test_session_with_valid_data():
    session = Session(
        session_id=uuid4(),
        user_id=1,
        refresh_token_hash="hashed-refresh-token",
        device="desktop",
        user_agent="Mozilla/5.0",
        ip_address=IPv4Address("127.0.0.1"),
        created_at=datetime.now(UTC),
        last_active_at=datetime.now(UTC),
        expires_at=datetime.now(UTC),
    )

    assert isinstance(session, Session)
    assert session.user_id == 1
    assert session.refresh_token_hash == "hashed-refresh-token"
    assert session.ip_address == IPv4Address("127.0.0.1")


@pytest.mark.parametrize(
    "field",
    ["created_at", "last_active_at", "expires_at"],
)
def test_session_rejects_naive_datetime(field):
    timestamps = {
        "created_at": datetime.now(UTC),
        "last_active_at": datetime.now(UTC),
        "expires_at": datetime.now(UTC),
    }

    timestamps[field] = datetime.now()

    with pytest.raises(ValueError):
        Session(
            session_id=uuid4(),
            user_id=1,
            refresh_token_hash="hashed-refresh-token",
            device="desktop",
            user_agent="Mozilla/5.0",
            ip_address=IPv4Address("127.0.0.1"),
            created_at=timestamps["created_at"],
            last_active_at=timestamps["last_active_at"],
            expires_at=timestamps["expires_at"],
        )


def test_session_response_does_not_expose_sensitive_data():
    assert "user_id" not in SessionResponse.model_fields
    assert "refresh_token_hash" not in SessionResponse.model_fields

    assert "session_id" in SessionResponse.model_fields
    assert "device" in SessionResponse.model_fields
    assert "user_agent" in SessionResponse.model_fields


def test_session_create_with_valid_data():
    session = SessionCreate(
        user_id=1,
        refresh_token_hash="hashed-refresh-token",
        device="desktop",
        user_agent="Mozilla/5.0",
        ip_address=IPv4Address("127.0.0.1"),
    )

    assert session.user_id == 1
    assert session.refresh_token_hash == "hashed-refresh-token"
    assert session.device == "desktop"
    assert session.user_agent == "Mozilla/5.0"
    assert session.ip_address == IPv4Address("127.0.0.1")


def test_session_create_rejects_invalid_user_id():
    with pytest.raises(ValueError):
        SessionCreate(
            user_id=0,
            refresh_token_hash="hashed-refresh-token",
            device="desktop",
            user_agent="Mozilla/5.0",
            ip_address=IPv4Address("127.0.0.1"),
        )


def test_session_create_rejects_empty_refresh_token_hash():
    with pytest.raises(ValueError):
        SessionCreate(
            user_id=1,
            refresh_token_hash="",
            device="desktop",
            user_agent="Mozilla/5.0",
            ip_address=IPv4Address("127.0.0.1"),
        )


def test_session_create_with_optional_fields_omitted():
    session = SessionCreate(
        user_id=1,
        refresh_token_hash="hashed-refresh-token",
    )

    assert session.device is None
    assert session.user_agent is None
    assert session.ip_address is None


def test_session_response_with_valid_data():
    session_id = uuid4()
    created_at = datetime.now(UTC)
    last_active_at = datetime.now(UTC)
    expires_at = datetime.now(UTC)

    response = SessionResponse(
        session_id=session_id,
        device="desktop",
        user_agent="Mozilla/5.0",
        ip_address=IPv4Address("127.0.0.1"),
        created_at=created_at,
        last_active_at=last_active_at,
        expires_at=expires_at,
    )

    assert response.session_id == session_id
    assert response.device == "desktop"
    assert response.user_agent == "Mozilla/5.0"
    assert response.ip_address == IPv4Address("127.0.0.1")
    assert response.created_at == created_at
    assert response.last_active_at == last_active_at
    assert response.expires_at == expires_at


@pytest.mark.parametrize(
    "field",
    ["created_at", "last_active_at", "expires_at"],
)
def test_session_response_rejects_naive_datetime(field):
    timestamps = {
        "created_at": datetime.now(UTC),
        "last_active_at": datetime.now(UTC),
        "expires_at": datetime.now(UTC),
    }

    timestamps[field] = datetime.now()

    with pytest.raises(ValueError):
        SessionResponse(
            session_id=uuid4(),
            device="desktop",
            user_agent="Mozilla/5.0",
            ip_address=IPv4Address("127.0.0.1"),
            created_at=timestamps["created_at"],
            last_active_at=timestamps["last_active_at"],
            expires_at=timestamps["expires_at"],
        )
