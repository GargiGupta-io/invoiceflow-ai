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

    auth_issuer: str = ""
    auth_client_id: str = ""
    auth_organization_claim: str = "custom:organization_id"
    auth_jwks_cache_seconds: int = Field(default=300, ge=1, le=3600)
    auth_jwks_timeout_seconds: float = Field(default=5, gt=0, le=30)
    auth_clock_skew_seconds: int = Field(default=30, ge=0, le=300)

    openai_api_key: SecretStr | None = None

    @property
    def sqlalchemy_database_url(self) -> str:
        return self.database_url.get_secret_value()

    @property
    def auth_configured(self) -> bool:
        return bool(self.auth_issuer.strip() and self.auth_client_id.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
