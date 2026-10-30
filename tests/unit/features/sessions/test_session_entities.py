from datetime import UTC, datetime
from ipaddress import IPv4Address
from uuid import uuid4

import pytest

from app.features.sessions.entities import Session


def test_session_with_valid_data():
    session = Session(
        session_id=uuid4(),
        user_id=1,
        jti="some-jti",
        device="desktop",
        ip_address=IPv4Address("127.0.0.1"),
        created_at=datetime.now(UTC),
        last_used_at=datetime.now(UTC),
    )

    assert isinstance(session, Session)
    assert session.user_id == 1
    assert session.jti == "some-jti"
    assert session.ip_address == IPv4Address("127.0.0.1")


@pytest.mark.parametrize(
    "field",
    [
        "created_at",
        "last_used_at",
    ],
)
def test_session_rejects_naive_datetime(field):
    timestamps = {
        "created_at": datetime.now(UTC),
        "last_used_at": datetime.now(UTC),
    }

    timestamps[field] = datetime.now()

    with pytest.raises(ValueError):
        Session(
            session_id=uuid4(),
            user_id=1,
            jti="some-jti",
            device="desktop",
            ip_address=IPv4Address("127.0.0.1"),
            created_at=timestamps["created_at"],
            last_used_at=timestamps["last_used_at"],
        )
