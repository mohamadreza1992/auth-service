import pytest

from app.core.exceptions import PasswordTooShort
from app.features.auth.password_policy import PasswordPolicy


def test_password_shorter_than_minimum_is_rejected():
    policy = PasswordPolicy()

    with pytest.raises(PasswordTooShort):
        policy.validate("a" * 11)


def test_password_at_minimum_length_is_accepted():
    policy = PasswordPolicy()

    result = policy.validate("a" * 12)

    assert result is None
