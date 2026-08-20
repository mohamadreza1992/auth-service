import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    app_name: str = Field(default="Auth Service")
    app_version: str = Field(default="0.1.0")
    app_debug: bool = Field(default=False)
    app_env: str

    database_url: str
    redis_url: str

    jwt_secret_key: str
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=30)
    jwt_refresh_token_expire_days: int = Field(default=30)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> AppSettings:
    environment = os.getenv("APP_ENV", "development")
    if environment == "test":
        env_file = ".env.test"
    else:
        env_file = ".env"
    return AppSettings(_env_file=env_file)  # pyright: ignore[reportCallIssue]


settings = get_settings()
