"""Application settings, loaded once from environment variables / .env."""
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must start with 'postgresql+asyncpg://'")
        if "sslmode" in value or "channel_binding" in value:
            raise ValueError(
                "asyncpg does not accept sslmode/channel_binding; use '?ssl=require'"
            )
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()