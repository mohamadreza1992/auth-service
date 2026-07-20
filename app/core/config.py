from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    app_name: str = Field(default="Auth Service")
    app_version: str = Field(default="0.1.0")
    app_debug: bool = Field(default=False)

    database_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()  # pyright: ignore[reportCallIssue]


settings = get_settings()
