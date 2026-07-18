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
