from pathlib import Path

import pytest

from app.features.auth.common_password_checker import CommonPasswordChecker


def test_common_password_is_detected(tmp_path: Path):
    passwords_file = tmp_path / "passwords.txt"
    passwords_file.write_text(
        "password123\nadmin123\n",
        encoding="utf-8",
    )

    checker = CommonPasswordChecker(passwords_file)

    assert checker.is_common("password123") is True


def test_common_password_check_is_case_insensitive(tmp_path: Path):
    passwords_file = tmp_path / "passwords.txt"
    passwords_file.write_text(
        "password123\n",
        encoding="utf-8",
    )

    checker = CommonPasswordChecker(passwords_file)

    assert checker.is_common("Password123") is True
    assert checker.is_common("PASSWORD123") is True


def test_non_common_password_is_not_detected(tmp_path: Path):
    passwords_file = tmp_path / "passwords.txt"
    passwords_file.write_text(
        "password123\nadmin123\n",
        encoding="utf-8",
    )

    checker = CommonPasswordChecker(passwords_file)

    assert checker.is_common("MyUniquePassword!927") is False


def test_missing_password_file_raises_error(tmp_path: Path):
    passwords_file = tmp_path / "missing_passwords.txt"

    with pytest.raises(RuntimeError, match="Could not load common passwords"):
        CommonPasswordChecker(passwords_file)


def test_empty_lines_are_ignored(tmp_path: Path):
    passwords_file = tmp_path / "passwords.txt"
    passwords_file.write_text(
        "\npassword123\n\nadmin123\n",
        encoding="utf-8",
    )

    checker = CommonPasswordChecker(passwords_file)

    assert checker.is_common("password123") is True
    assert checker.is_common("") is False
