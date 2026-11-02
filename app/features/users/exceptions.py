from app.core.exceptions import ConflictError, NotFoundError, RuleViolationError


class UserNotFound(NotFoundError):
    """Raised when a user does not exist."""

    code = "USER_NOT_FOUND"
    message = "User not found"


class UserAlreadyExists(ConflictError):
    """Raised when a user with the same unique identity already exists."""

    code = "USER_ALREADY_EXISTS"
    message = "User already exists"


class UserInactive(RuleViolationError):
    """Raised when an operation requires an active user."""

    code = "USER_INACTIVE"
    message = "User account is inactive"


class ProfileNotFound(NotFoundError):
    code = "PROFILE_NOT_FOUND"
    message = "User profile not found"
