from datetime import datetime

from pydantic import UUID4, BaseModel, Field, IPvAnyAddress, field_validator


class SessionResponse(BaseModel):
    created_at: datetime
    last_used_at: datetime
    session_id: UUID4
    device: str | None = None
    ip_address: IPvAnyAddress | None = None

    @field_validator(
        "created_at",
        "last_used_at",
    )
    @classmethod
    def validate_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("datetime must be timezone-aware")

        return value


class SessionCreate(BaseModel):
    user_id: int = Field(gt=0)
    jti: str = Field(min_length=1)
    device: str | None = None
    ip_address: IPvAnyAddress | None = None
