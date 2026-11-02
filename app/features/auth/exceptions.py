from app.core.exceptions import AuthenticationError, RuleViolationError


class InvalidCredentials(AuthenticationError):
    """Raised when provided authentication credentials are invalid."""

    code = "INVALID_CREDENTIALS"
    message = "Invalid email or password"


class ExpiredToken(AuthenticationError):
    """Raised when a token has expired."""

    code = "EXPIRED_TOKEN"
    message = "Token has expired"


class PasswordMismatch(RuleViolationError):
    """Raised when password confirmation does not match."""

    code = "PASSWORD_MISMATCH"
    message = "Passwords do not match"


class PasswordTooShort(RuleViolationError):
    """Raised when a password does not meet minimum length requirements."""

    code = "PASSWORD_TOO_SHORT"
    message = "Password does not meet minimum length requirements"


class PasswordTooWeak(RuleViolationError):
    """Raised when a password does not meet complexity requirements."""

    code = "PASSWORD_TOO_WEAK"
    message = "Password does not meet complexity requirements"


class CommonPasswordRejected(RuleViolationError):
    """Raised when a password is found in the common or leaked password list."""

    code = "COMMON_PASSWORD_REJECTED"
    message = "This password is not allowed"


class InvalidRefreshToken(AuthenticationError):
    code = "INVALID_REFRESH_TOKEN"
    message = "Invalid refresh token"


class RevokedToken(AuthenticationError):
    code = "REVOKED_TOKEN"
    message = "Token has been revoked"
