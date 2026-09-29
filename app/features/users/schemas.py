from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserProfileResponse(BaseModel):
    id: int
    user_id: int
    first_name: str | None
    last_name: str | None
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProfileUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None


class ProfileReplace(BaseModel):
    first_name: str
    last_name: str
    avatar_url: str
