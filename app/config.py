from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "development"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)

    database_url: SecretStr = SecretStr(
        "postgresql+psycopg://invoiceflow:invoiceflow@localhost:5432/invoiceflow"
    )
    database_pool_size: int = Field(default=5, ge=1)
    database_max_overflow: int = Field(default=5, ge=0)
    database_pool_timeout_seconds: int = Field(default=30, ge=1)
    database_echo: bool = False

    openai_api_key: SecretStr | None = None

    @property
    def sqlalchemy_database_url(self) -> str:
        return self.database_url.get_secret_value()


@lru_cache
def get_settings() -> Settings:
    return Settings()
