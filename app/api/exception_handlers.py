import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from app.api.schemas import ErrorDetail, ErrorResponse
from app.core.exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    InfrastructureError,
    NotFoundError,
    RuleViolationError,
)

logger = logging.getLogger(__name__)


EXCEPTION_STATUS_CODES: dict[type[AppError], int] = {
    AuthenticationError: 401,
    AuthorizationError: 403,
    NotFoundError: 404,
    ConflictError: 409,
    RuleViolationError: 422,
    InfrastructureError: 503,
    AppError: 500,
}


async def app_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle application-level exceptions."""

    if not isinstance(exc, AppError):
        raise TypeError("Expected an AppError instance")

    status_code = next(
        (
            status
            for exception_type, status in EXCEPTION_STATUS_CODES.items()
            if isinstance(exc, exception_type)
        ),
        500,
    )

    if status_code >= 500:
        logger.error(
            "Application error: %s",
            exc.code,
            extra={"path": request.url.path},
        )

    response = ErrorResponse(
        error=ErrorDetail(
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )
    )

    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(exclude_none=True),
    )


async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected application exceptions."""

    logger.exception(
        "Unexpected error occurred",
        extra={"path": request.url.path},
    )

    response = ErrorResponse(
        error=ErrorDetail(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
        )
    )

    return JSONResponse(
        status_code=500,
        content=response.model_dump(exclude_none=True),
    )
