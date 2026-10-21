import pytest

from app.core.exceptions import (
    CommonPasswordRejected,
    PasswordTooShort,
    PasswordTooWeak,
)
from app.features.auth.password_policy import PasswordPolicy


def test_password_shorter_than_minimum_is_rejected():
    policy = PasswordPolicy()

    with pytest.raises(PasswordTooShort):
        policy.validate("a" * 11)


def test_password_at_minimum_length_is_accepted():
    policy = PasswordPolicy()

    result = policy.validate("Abcdefgh12!@")

    assert result is None


def test_password_without_number_is_rejected():
    policy = PasswordPolicy()
    password = "Abcdfgh#@hFD"

    with pytest.raises(PasswordTooWeak):
        policy.validate(password)


def test_password_without_uppercase_is_rejected():
    policy = PasswordPolicy()
    password = "abcdfgh#4d@hfd"

    with pytest.raises(PasswordTooWeak):
        policy.validate(password)


def test_password_without_lowercase_is_rejected():
    policy = PasswordPolicy()
    password = "ABVNHJG#@HHF4D"

    with pytest.raises(PasswordTooWeak):
        policy.validate(password)


def test_password_without_special_char_is_rejected():
    policy = PasswordPolicy()
    password = "Abcdfghjhg45hFD"

    with pytest.raises(PasswordTooWeak):
        policy.validate(password)


def test_common_password_is_rejected(tmp_path):
    from app.features.auth.common_password_checker import CommonPasswordChecker

    passwords_file = tmp_path / "passwords.txt"
    passwords_file.write_text(
        "Abcdefgh12!@\n",
        encoding="utf-8",
    )

    checker = CommonPasswordChecker(passwords_file)
    policy = PasswordPolicy(common_password_checker=checker)

    with pytest.raises(CommonPasswordRejected):
        policy.validate("Abcdefgh12!@")


def test_non_common_password_is_accepted(tmp_path):
    from app.features.auth.common_password_checker import CommonPasswordChecker

    passwords_file = tmp_path / "passwords.txt"
    passwords_file.write_text(
        "password123\n",
        encoding="utf-8",
    )

    checker = CommonPasswordChecker(passwords_file)
    policy = PasswordPolicy(common_password_checker=checker)

    assert policy.validate("MyUniquePassword!927") is None
