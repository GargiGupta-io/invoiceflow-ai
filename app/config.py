from __future__ import annotations

from functools import lru_cache
from typing import Literal, Self
from urllib.parse import urlparse

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


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
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    cloudwatch_metric_namespace: str = Field(default="InvoiceFlow", min_length=1, max_length=255)

    database_url: SecretStr | None = SecretStr(
        "postgresql+psycopg://invoiceflow:invoiceflow@localhost:5432/invoiceflow"
    )
    database_host: str = ""
    database_port: int = Field(default=5432, ge=1, le=65535)
    database_name: str = ""
    database_user: str = ""
    database_password: SecretStr | None = None
    database_pool_size: int = Field(default=5, ge=1)
    database_max_overflow: int = Field(default=5, ge=0)
    database_pool_timeout_seconds: int = Field(default=30, ge=1)
    database_echo: bool = False

    auth_issuer: str = ""
    auth_client_id: str = ""
    auth_browser_domain: str = ""
    auth_redirect_uri: str = ""
    auth_logout_uri: str = ""
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
    sqs_visibility_heartbeat_seconds: int = Field(default=30, ge=5, le=3600)
    sqs_retry_base_delay_seconds: int = Field(default=30, ge=1, le=43200)
    sqs_retry_max_delay_seconds: int = Field(default=900, ge=1, le=43200)
    sqs_redrive_max_receive_count: int = Field(default=4, ge=2, le=1000)
    worker_stale_job_seconds: int = Field(default=3600, ge=60, le=43200)
    worker_extractor_mode: Literal["heuristic", "auto", "llm"] = "heuristic"

    upload_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1, le=100 * 1024 * 1024)
    upload_max_pdf_pages: int = Field(default=25, ge=1, le=500)
    upload_max_filename_length: int = Field(default=255, ge=32, le=255)
    document_retention_days: int = Field(default=90, ge=1, le=3650)
    retention_delete_batch_size: int = Field(default=100, ge=1, le=1000)

    openai_api_key: SecretStr | None = None

    @model_validator(mode="after")
    def validate_s3_encryption(self) -> Self:
        database_url = (
            self.database_url.get_secret_value().strip() if self.database_url else ""
        )
        database_parts = (
            self.database_host.strip(),
            self.database_name.strip(),
            self.database_user.strip(),
            self.database_password.get_secret_value().strip()
            if self.database_password
            else "",
        )
        if not database_url and not all(database_parts):
            raise ValueError(
                "Configure DATABASE_URL or all of DATABASE_HOST, DATABASE_NAME, "
                "DATABASE_USER, and DATABASE_PASSWORD."
            )
        if self.s3_sse_algorithm == "aws:kms" and not (self.s3_kms_key_id or "").strip():
            raise ValueError("S3_KMS_KEY_ID is required when S3_SSE_ALGORITHM is aws:kms.")
        if self.sqs_visibility_heartbeat_seconds >= self.sqs_visibility_timeout_seconds:
            raise ValueError(
                "SQS_VISIBILITY_HEARTBEAT_SECONDS must be less than "
                "SQS_VISIBILITY_TIMEOUT_SECONDS."
            )
        if self.sqs_retry_base_delay_seconds > self.sqs_retry_max_delay_seconds:
            raise ValueError(
                "SQS_RETRY_BASE_DELAY_SECONDS cannot exceed SQS_RETRY_MAX_DELAY_SECONDS."
            )
        if self.worker_stale_job_seconds <= self.sqs_visibility_timeout_seconds:
            raise ValueError(
                "WORKER_STALE_JOB_SECONDS must exceed SQS_VISIBILITY_TIMEOUT_SECONDS."
            )
        browser_auth_values = (
            self.auth_browser_domain.strip(),
            self.auth_redirect_uri.strip(),
            self.auth_logout_uri.strip(),
        )
        if any(browser_auth_values) and not all(browser_auth_values):
            raise ValueError(
                "Configure AUTH_BROWSER_DOMAIN, AUTH_REDIRECT_URI, and "
                "AUTH_LOGOUT_URI together."
            )
        if all(browser_auth_values):
            if not self.auth_configured:
                raise ValueError(
                    "AUTH_ISSUER and AUTH_CLIENT_ID are required for browser login."
                )
            browser_domain = urlparse(browser_auth_values[0])
            if browser_domain.scheme != "https" or not browser_domain.netloc:
                raise ValueError("AUTH_BROWSER_DOMAIN must be an HTTPS URL.")
            for field_name, value in (
                ("AUTH_REDIRECT_URI", browser_auth_values[1]),
                ("AUTH_LOGOUT_URI", browser_auth_values[2]),
            ):
                parsed = urlparse(value)
                local_http = parsed.scheme == "http" and parsed.hostname in {
                    "127.0.0.1",
                    "localhost",
                }
                if not parsed.netloc or (parsed.scheme != "https" and not local_http):
                    raise ValueError(
                        f"{field_name} must use HTTPS or local HTTP development."
                    )
        return self

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            database_url = self.database_url.get_secret_value().strip()
            if database_url:
                return database_url

        return URL.create(
            drivername="postgresql+psycopg",
            username=self.database_user.strip(),
            password=self.database_password.get_secret_value()
            if self.database_password
            else None,
            host=self.database_host.strip(),
            port=self.database_port,
            database=self.database_name.strip(),
        ).render_as_string(hide_password=False)

    @property
    def auth_configured(self) -> bool:
        return bool(self.auth_issuer.strip() and self.auth_client_id.strip())

    @property
    def auth_browser_configured(self) -> bool:
        return bool(
            self.auth_configured
            and self.auth_browser_domain.strip()
            and self.auth_redirect_uri.strip()
            and self.auth_logout_uri.strip()
        )

    @property
    def s3_configured(self) -> bool:
        return bool(self.s3_bucket_name.strip())

    @property
    def sqs_configured(self) -> bool:
        return bool(self.sqs_queue_url.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
