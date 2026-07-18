from __future__ import annotations

from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
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

    aws_region: str = "ap-south-1"
    aws_endpoint_url: str | None = None
    s3_bucket_name: str = ""
    s3_quarantine_prefix: str = "quarantine"
    s3_validated_prefix: str = "validated"
    s3_sse_algorithm: Literal["AES256", "aws:kms"] = "AES256"
    s3_kms_key_id: str | None = None
    s3_presigned_url_ttl_seconds: int = Field(default=300, ge=60, le=300)
    sqs_queue_url: str = ""
    sqs_wait_time_seconds: int = Field(default=20, ge=0, le=20)
    sqs_visibility_timeout_seconds: int = Field(default=120, ge=30, le=43200)
    worker_extractor_mode: Literal["heuristic", "auto", "llm"] = "heuristic"

    upload_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1, le=100 * 1024 * 1024)
    upload_max_pdf_pages: int = Field(default=25, ge=1, le=500)
    upload_max_filename_length: int = Field(default=255, ge=32, le=255)

    openai_api_key: SecretStr | None = None

    @model_validator(mode="after")
    def validate_s3_encryption(self) -> Self:
        if self.s3_sse_algorithm == "aws:kms" and not (self.s3_kms_key_id or "").strip():
            raise ValueError("S3_KMS_KEY_ID is required when S3_SSE_ALGORITHM is aws:kms.")
        return self

    @property
    def sqlalchemy_database_url(self) -> str:
        return self.database_url.get_secret_value()

    @property
    def auth_configured(self) -> bool:
        return bool(self.auth_issuer.strip() and self.auth_client_id.strip())

    @property
    def s3_configured(self) -> bool:
        return bool(self.s3_bucket_name.strip())

    @property
    def sqs_configured(self) -> bool:
        return bool(self.sqs_queue_url.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
