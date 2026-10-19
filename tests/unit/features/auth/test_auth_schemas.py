import pytest
from pydantic import ValidationError

from app.features.auth.schemas import UserCreate


def test_user_create_rejects_password_shorter_than_12_characters():
    with pytest.raises(ValidationError):
        UserCreate(
            email="user@example.com",
            password="a" * 11,
        )


def test_user_create_accepts_password_with_12_characters():
    user = UserCreate(
        email="user@example.com",
        password="a" * 12,
    )

    assert len(user.password) == 12
