from app.core.exceptions import (
    CommonPasswordRejected,
    PasswordTooShort,
    PasswordTooWeak,
)
from app.features.auth.common_password_checker import CommonPasswordChecker


class PasswordPolicy:
    MIN_PASSWORD_LENGTH = 12

    def __init__(
        self,
        common_password_checker: CommonPasswordChecker | None = None,
    ) -> None:
        self.common_password_checker = (
            common_password_checker or CommonPasswordChecker()
        )

    def validate(self, password: str) -> None:
        if len(password) < self.MIN_PASSWORD_LENGTH:
            raise PasswordTooShort()

        has_uppercase = any("A" <= char <= "Z" for char in password)
        has_lowercase = any("a" <= char <= "z" for char in password)
        has_digit = any("0" <= char <= "9" for char in password)
        has_special = any(
            not char.isalnum() and not char.isspace() for char in password
        )

        if not (has_uppercase and has_lowercase and has_digit and has_special):
            raise PasswordTooWeak()

        if self.common_password_checker.is_common(password):
            raise CommonPasswordRejected()
