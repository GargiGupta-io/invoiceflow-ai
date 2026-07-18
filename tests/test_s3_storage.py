from __future__ import annotations

import unittest
import uuid
from typing import Any

from botocore.exceptions import ClientError
from pydantic import ValidationError

from app.config import Settings
from app.storage import S3ObjectStorage, StorageOperationError, build_document_keys
from app.storage.keys import normalize_storage_prefix, validate_document_key


class RecordingS3Client:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.fail_copy = False
        self.fail_put = False

    def put_object(self, **request: Any) -> dict[str, str]:
        self.calls.append(("put_object", request))
        if self.fail_put:
            raise ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "secret provider detail"}},
                "PutObject",
            )
        return {"ETag": "upload-etag", "VersionId": "upload-version"}

    def copy_object(self, **request: Any) -> dict[str, Any]:
        self.calls.append(("copy_object", request))
        if self.fail_copy:
            raise ClientError(
                {"Error": {"Code": "ServiceUnavailable", "Message": "private bucket detail"}},
                "CopyObject",
            )
        return {"CopyObjectResult": {"ETag": "copy-etag"}, "VersionId": "copy-version"}

    def delete_object(self, **request: Any) -> dict[str, Any]:
        self.calls.append(("delete_object", request))
        return {}


class DocumentStorageKeyTests(unittest.TestCase):
    def test_document_keys_use_only_uuid_tenant_identifiers(self) -> None:
        organization_id = uuid.uuid4()
        document_id = uuid.uuid4()

        keys = build_document_keys(
            organization_id=organization_id,
            document_id=document_id,
        )

        expected_path = f"{organization_id}/{document_id}"
        self.assertEqual(keys.quarantine_key, f"quarantine/{expected_path}")
        self.assertEqual(keys.validated_key, f"validated/{expected_path}")
        self.assertNotIn("invoice.pdf", keys.quarantine_key)

    def test_unsafe_or_empty_prefixes_are_rejected(self) -> None:
        for prefix in ("", "/", "quarantine/../private", "quarantine//nested"):
            with self.subTest(prefix=prefix):
                with self.assertRaises(ValueError):
                    normalize_storage_prefix(prefix)

    def test_document_key_requires_uuid_tenant_and_document_segments(self) -> None:
        invalid_keys = (
            "quarantine/../private/document",
            "quarantine/tenant/document",
            f"quarantine/{uuid.uuid4()}",
            f"quarantine/{uuid.uuid4()}/{uuid.uuid4()}/extra",
        )
        for key in invalid_keys:
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    validate_document_key(key=key, prefix="quarantine")


class S3ObjectStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = RecordingS3Client()
        self.storage = S3ObjectStorage(
            client=self.client,
            bucket_name="invoiceflow-private-documents",
        )
        self.keys = build_document_keys(
            organization_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
        )

    def test_quarantine_upload_is_private_and_encrypted(self) -> None:
        stored = self.storage.upload_quarantined(
            key=self.keys.quarantine_key,
            content=b"document bytes",
            content_type="application/pdf",
            metadata={"original-filename": "invoice.pdf"},
        )

        operation, request = self.client.calls[0]
        self.assertEqual(operation, "put_object")
        self.assertEqual(request["ServerSideEncryption"], "AES256")
        self.assertEqual(request["ContentType"], "application/pdf")
        self.assertEqual(request["Metadata"]["original-filename"], "invoice.pdf")
        self.assertNotIn("ACL", request)
        self.assertEqual(stored.key, self.keys.quarantine_key)
        self.assertEqual(stored.etag, "upload-etag")

    def test_kms_upload_includes_the_configured_key(self) -> None:
        storage = S3ObjectStorage(
            client=self.client,
            bucket_name="invoiceflow-private-documents",
            sse_algorithm="aws:kms",
            kms_key_id="alias/invoiceflow-documents",
        )

        storage.upload_quarantined(
            key=self.keys.quarantine_key,
            content=b"document bytes",
            content_type="application/pdf",
        )

        request = self.client.calls[0][1]
        self.assertEqual(request["ServerSideEncryption"], "aws:kms")
        self.assertEqual(request["SSEKMSKeyId"], "alias/invoiceflow-documents")

    def test_promotion_copies_before_removing_quarantine_object(self) -> None:
        stored = self.storage.promote(
            source_key=self.keys.quarantine_key,
            destination_key=self.keys.validated_key,
        )

        self.assertEqual(
            [call[0] for call in self.client.calls],
            ["copy_object", "delete_object"],
        )
        copy_request = self.client.calls[0][1]
        self.assertEqual(
            copy_request["CopySource"],
            {"Bucket": "invoiceflow-private-documents", "Key": self.keys.quarantine_key},
        )
        self.assertNotIn("ACL", copy_request)
        self.assertEqual(stored.key, self.keys.validated_key)
        self.assertEqual(stored.etag, "copy-etag")

    def test_failed_promotion_keeps_the_quarantine_object(self) -> None:
        self.client.fail_copy = True

        with self.assertRaises(StorageOperationError):
            self.storage.promote(
                source_key=self.keys.quarantine_key,
                destination_key=self.keys.validated_key,
            )

        self.assertEqual([call[0] for call in self.client.calls], ["copy_object"])

    def test_provider_failure_is_redacted(self) -> None:
        self.client.fail_put = True

        with self.assertRaises(StorageOperationError) as context:
            self.storage.upload_quarantined(
                key=self.keys.quarantine_key,
                content=b"document bytes",
                content_type="application/pdf",
            )

        message = str(context.exception)
        self.assertEqual(message, "Storage operation failed.")
        self.assertNotIn("secret provider detail", message)
        self.assertNotIn(self.keys.quarantine_key, message)

    def test_keys_outside_managed_prefixes_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.storage.delete(key="unmanaged/tenant/document")
        self.assertEqual(self.client.calls, [])

    def test_empty_bucket_configuration_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            S3ObjectStorage(client=self.client, bucket_name="  ")


class S3SettingsTests(unittest.TestCase):
    def test_s3_configuration_is_detected_from_bucket_name(self) -> None:
        settings = Settings(_env_file=None, s3_bucket_name="invoiceflow-private-documents")
        self.assertTrue(settings.s3_configured)

    def test_kms_encryption_requires_a_key(self) -> None:
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, s3_sse_algorithm="aws:kms")


if __name__ == "__main__":
    unittest.main()
