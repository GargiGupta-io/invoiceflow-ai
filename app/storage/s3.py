from __future__ import annotations

from typing import Any, Mapping

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import Settings
from app.storage.interface import StorageBody, StorageOperationError, StoredObject
from app.storage.keys import normalize_storage_prefix, validate_document_key


class S3ObjectStorage:
    def __init__(
        self,
        *,
        client: Any,
        bucket_name: str,
        quarantine_prefix: str = "quarantine",
        validated_prefix: str = "validated",
        sse_algorithm: str = "AES256",
        kms_key_id: str | None = None,
    ) -> None:
        if not bucket_name.strip():
            raise ValueError("S3 bucket name is required.")
        if sse_algorithm not in {"AES256", "aws:kms"}:
            raise ValueError("Unsupported S3 server-side encryption algorithm.")
        if sse_algorithm == "aws:kms" and not (kms_key_id or "").strip():
            raise ValueError("A KMS key is required for aws:kms encryption.")

        self.client = client
        self.bucket_name = bucket_name.strip()
        self.quarantine_prefix = normalize_storage_prefix(quarantine_prefix)
        self.validated_prefix = normalize_storage_prefix(validated_prefix)
        self.sse_algorithm = sse_algorithm
        self.kms_key_id = kms_key_id

    @classmethod
    def from_settings(cls, settings: Settings) -> S3ObjectStorage:
        if not settings.s3_configured:
            raise ValueError("S3 storage is not configured.")

        client = boto3.client(
            "s3",
            region_name=settings.aws_region,
            endpoint_url=settings.aws_endpoint_url or None,
            config=Config(
                signature_version="s3v4",
                connect_timeout=5,
                read_timeout=30,
                retries={"mode": "standard", "max_attempts": 4},
            ),
        )
        return cls(
            client=client,
            bucket_name=settings.s3_bucket_name,
            quarantine_prefix=settings.s3_quarantine_prefix,
            validated_prefix=settings.s3_validated_prefix,
            sse_algorithm=settings.s3_sse_algorithm,
            kms_key_id=settings.s3_kms_key_id,
        )

    def check_health(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except (BotoCoreError, ClientError):
            raise StorageOperationError("Storage operation failed.") from None

    def upload_quarantined(
        self,
        *,
        key: str,
        content: StorageBody,
        content_type: str,
        metadata: Mapping[str, str] | None = None,
    ) -> StoredObject:
        self._require_prefix(key, self.quarantine_prefix)
        request: dict[str, Any] = {
            "Bucket": self.bucket_name,
            "Key": key,
            "Body": content,
            "ContentType": content_type,
            "Metadata": dict(metadata or {}),
            **self._encryption_parameters(),
        }
        try:
            response = self.client.put_object(**request)
        except (BotoCoreError, ClientError):
            raise StorageOperationError("Storage operation failed.") from None
        return self._stored_object(key=key, response=response)

    def promote(self, *, source_key: str, destination_key: str) -> StoredObject:
        self._require_prefix(source_key, self.quarantine_prefix)
        self._require_prefix(destination_key, self.validated_prefix)
        try:
            response = self.client.copy_object(
                Bucket=self.bucket_name,
                Key=destination_key,
                CopySource={"Bucket": self.bucket_name, "Key": source_key},
                **self._encryption_parameters(),
            )
            self.client.delete_object(Bucket=self.bucket_name, Key=source_key)
        except (BotoCoreError, ClientError):
            raise StorageOperationError("Storage operation failed.") from None

        copy_result = response.get("CopyObjectResult", {})
        return StoredObject(
            bucket=self.bucket_name,
            key=destination_key,
            etag=copy_result.get("ETag"),
            version_id=response.get("VersionId"),
        )

    def read(self, *, key: str, max_bytes: int) -> bytes:
        self._require_managed_key(key)
        if max_bytes < 1:
            raise ValueError("Object read limit must be positive.")
        body = None
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=key)
            content_length = response.get("ContentLength")
            if isinstance(content_length, int) and content_length > max_bytes:
                raise StorageOperationError("Storage operation failed.")
            body = response.get("Body")
            if body is None or not hasattr(body, "read"):
                raise StorageOperationError("Storage operation failed.")
            content = body.read(max_bytes + 1)
        except StorageOperationError:
            raise
        except (BotoCoreError, ClientError, OSError):
            raise StorageOperationError("Storage operation failed.") from None
        finally:
            if body is not None and hasattr(body, "close"):
                body.close()

        if not isinstance(content, bytes) or len(content) > max_bytes:
            raise StorageOperationError("Storage operation failed.")
        return content

    def create_download_url(self, *, key: str, expires_in_seconds: int) -> str:
        self._require_prefix(key, self.validated_prefix)
        if not 60 <= expires_in_seconds <= 300:
            raise ValueError("Download URL lifetime must be between 60 and 300 seconds.")
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expires_in_seconds,
                HttpMethod="GET",
            )
        except (BotoCoreError, ClientError):
            raise StorageOperationError("Storage operation failed.") from None

    def delete(self, *, key: str) -> None:
        self._require_managed_key(key)
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
        except (BotoCoreError, ClientError):
            raise StorageOperationError("Storage operation failed.") from None

    def _encryption_parameters(self) -> dict[str, str]:
        parameters = {"ServerSideEncryption": self.sse_algorithm}
        if self.sse_algorithm == "aws:kms" and self.kms_key_id:
            parameters["SSEKMSKeyId"] = self.kms_key_id
        return parameters

    def _require_managed_key(self, key: str) -> None:
        for prefix in (self.quarantine_prefix, self.validated_prefix):
            try:
                validate_document_key(key=key, prefix=prefix)
                return
            except ValueError:
                continue
        raise ValueError("Object key is outside the managed storage prefixes.")

    @staticmethod
    def _require_prefix(key: str, prefix: str) -> None:
        validate_document_key(key=key, prefix=prefix)

    def _stored_object(self, *, key: str, response: Mapping[str, Any]) -> StoredObject:
        return StoredObject(
            bucket=self.bucket_name,
            key=key,
            etag=response.get("ETag"),
            version_id=response.get("VersionId"),
        )
