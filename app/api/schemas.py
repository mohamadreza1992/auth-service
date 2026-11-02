from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    """Represents the details of an API error."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error message")
    details: dict[str, Any] | None = Field(
        default=None,
        description="Additional error information",
    )


class ErrorResponse(BaseModel):
    """Standard API error response."""

    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail
