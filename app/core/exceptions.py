from typing import Any


class AppError(Exception):
    """Base exception for all application-level errors."""

    code = "APPLICATION_ERROR"
    message = "An application error occurred"

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message if message is not None else type(self).message
        self.details = details

        super().__init__(self.message)


class AuthenticationError(AppError):
    """Raised when authentication fails."""

    code = "AUTHENTICATION_ERROR"
    message = "Authentication failed"


class AuthorizationError(AppError):
    """Raised when a user is not allowed to perform an operation."""

    code = "AUTHORIZATION_ERROR"
    message = "Permission denied"


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    code = "RESOURCE_NOT_FOUND"
    message = "Resource not found"


class ConflictError(AppError):
    """Raised when an operation conflicts with the current state."""

    code = "RESOURCE_CONFLICT"
    message = "Resource conflict"


class RuleViolationError(AppError):
    """Raised when a business rule is violated."""

    code = "BUSINESS_RULE_VIOLATION"
    message = "Business rule violation"


class InfrastructureError(AppError):
    """Raised when an infrastructure dependency fails."""

    code = "INFRASTRUCTURE_ERROR"
    message = "An infrastructure error occurred"


class InvalidToken(AuthenticationError):
    """Raised when a token is invalid."""

    code = "INVALID_TOKEN"
    message = "Invalid token"
