from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class UserEntity:
    id: int
    email: str
    password_hash: str
    is_active: bool
    created_at: datetime | None = None


@dataclass(slots=True)
class UserProfileEntity:
    user_id: int
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None
