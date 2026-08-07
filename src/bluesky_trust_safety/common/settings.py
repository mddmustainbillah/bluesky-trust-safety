from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="BTS_",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    environment: Literal["local", "test", "staging", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    redis_url: SecretStr
    database_url: SecretStr


@lru_cache
def get_settings() -> Settings:
    """Load and cache application settings."""

    return Settings()
