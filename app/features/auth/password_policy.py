from app.core.exceptions import PasswordTooShort


class PasswordPolicy:
    MIN_PASSWORD_LENGTH = 12

    def validate(self, password: str) -> None:
        if len(password) < self.MIN_PASSWORD_LENGTH:
            raise PasswordTooShort()
