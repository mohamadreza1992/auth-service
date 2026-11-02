from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError


class SessionNotFound(NotFoundError):
    """Raised when a session does not exist."""

    code = "SESSION_NOT_FOUND"
    message = "Session not found"


class SessionRevoked(AuthenticationError):
    """Raised when an operation uses a revoked session."""

    code = "SESSION_REVOKED"
    message = "Session has been revoked"


class RefreshTokenReuseDetected(AuthenticationError):
    """Raised when a previously rotated refresh token is reused."""

    code = "REFRESH_TOKEN_REUSE_DETECTED"
    message = "Refresh token reuse detected"


class InvalidSession(AuthenticationError):
    code = "INVALID_SESSION"
    message = "Invalid session"


class SessionOperationInProgress(ConflictError):
    code = "SESSION_OPERATION_IN_PROGRESS"
    message = "A session operation is already in progress"
