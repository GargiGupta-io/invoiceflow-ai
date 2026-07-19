from __future__ import annotations

import unittest
import uuid
from io import BytesIO
from typing import Any, Mapping
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlalchemy.exc import SQLAlchemyError

from api.v2 import router
from app.auth.claims import VerifiedIdentity
from app.auth.dependencies import get_database, get_token_verifier
from app.db import Base, Organization, User
from app.db.repositories import AuditEventRepository, DocumentRepository
from app.db.session import create_database
from app.db.tenant import TenantContext
from app.ingest import UploadPersistenceError, UploadValidator, persist_quarantined_upload
from app.storage import StorageOperationError, StoredObject, get_object_storage


def build_pdf(page_count: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=612, height=792)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


class StaticTokenVerifier:
    def __init__(self, identity: VerifiedIdentity) -> None:
        self.identity = identity

    def verify(self, _token: str) -> VerifiedIdentity:
        return self.identity


class RecordingObjectStorage:
    def __init__(self) -> None:
        self.uploads: list[dict[str, Any]] = []
        self.deletes: list[str] = []
        self.fail_upload = False
        self.fail_delete = False

    def upload_quarantined(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        metadata: Mapping[str, str] | None = None,
    ) -> StoredObject:
        self.uploads.append(
            {
                "key": key,
                "content": content,
                "content_type": content_type,
                "metadata": dict(metadata or {}),
            }
        )
        if self.fail_upload:
            raise StorageOperationError("Storage operation failed.")
        return StoredObject(bucket="private-test-bucket", key=key)

    def promote(self, *, source_key: str, destination_key: str) -> StoredObject:
        raise AssertionError("Promotion is not part of the upload endpoint.")

    def delete(self, *, key: str) -> None:
        self.deletes.append(key)
        if self.fail_delete:
            raise StorageOperationError("Storage cleanup failed.")


class SecureUploadApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = create_database(database_url="sqlite://")
        Base.metadata.create_all(self.database.engine)
        self.organization_a = uuid.uuid4()
        self.organization_b = uuid.uuid4()
        self.user_a = uuid.uuid4()
        self.user_b = uuid.uuid4()
        self.subject_a = "cognito-upload-user-a"
        self.subject_b = "cognito-upload-user-b"

        with self.database.transaction() as session:
            session.add_all(
                [
                    Organization(id=self.organization_a, name="Organization A"),
                    Organization(id=self.organization_b, name="Organization B"),
                    User(
                        id=self.user_a,
                        organization_id=self.organization_a,
                        external_subject=self.subject_a,
                        email="uploader-a@example.com",
                    ),
                    User(
                        id=self.user_b,
                        organization_id=self.organization_b,
                        external_subject=self.subject_b,
                        email="uploader-b@example.com",
                    ),
                ]
            )

        self.storage = RecordingObjectStorage()
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[get_database] = lambda: self.database
        self.app.dependency_overrides[get_object_storage] = lambda: self.storage
        self.set_identity(self.organization_a, self.subject_a)
        self.client = TestClient(self.app)
        self.headers = {"Authorization": "Bearer valid-upload-token"}

    def tearDown(self) -> None:
        self.database.dispose()

    def set_identity(
        self,
        organization_id: uuid.UUID,
        subject: str,
        *,
        scopes: frozenset[str] = frozenset({"invoiceflow.upload", "invoiceflow.read"}),
    ) -> None:
        identity = VerifiedIdentity(
            subject=subject,
            organization_id=organization_id,
            username=None,
            scopes=scopes,
        )
        self.app.dependency_overrides[get_token_verifier] = lambda: StaticTokenVerifier(identity)

    def upload_pdf(self, *, filename: str = "invoice.pdf", content_type: str = "application/pdf"):
        return self.client.post(
            "/v2/documents",
            headers=self.headers,
            files={"file": (filename, build_pdf(page_count=2), content_type)},
        )

    def test_upload_creates_tenant_document_audit_and_quarantine_object(self) -> None:
        response = self.upload_pdf(filename="July invoice (final).pdf")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers["cache-control"], "no-store")
        payload = response.json()
        self.assertNotIn("storage_key", payload["document"])
        self.assertNotIn("bucket", payload)
        self.assertEqual(payload["document"]["status"], "quarantined")

        with self.database.transaction() as session:
            tenant = TenantContext(self.organization_a, self.user_a)
            document = DocumentRepository(session, tenant).require(
                uuid.UUID(payload["document"]["id"])
            )
            events = AuditEventRepository(session, tenant).list_for_resource(
                "document",
                str(document.id),
            )

        self.assertEqual(document.organization_id, self.organization_a)
        self.assertEqual(document.uploaded_by_user_id, self.user_a)
        self.assertEqual(document.original_filename, "July invoice (final).pdf")
        self.assertIsNotNone(document.retention_until)
        self.assertEqual(events[0].action, "document.uploaded")
        self.assertEqual(events[0].request_id, payload["request_id"])
        self.assertNotIn("storage_key", events[0].safe_metadata)
        self.assertNotIn("original_filename", events[0].safe_metadata)

        upload = self.storage.uploads[0]
        self.assertIn(str(self.organization_a), upload["key"])
        self.assertNotIn("July invoice", upload["key"])
        self.assertEqual(upload["metadata"]["original-filename"], "July invoice _final_.pdf")

    def test_verified_identity_controls_document_ownership(self) -> None:
        response_a = self.upload_pdf()
        self.set_identity(self.organization_b, self.subject_b)
        response_b = self.upload_pdf(filename="invoice-b.pdf")

        self.assertEqual(response_a.status_code, 201)
        self.assertEqual(response_b.status_code, 201)
        with self.database.transaction() as session:
            documents_a = DocumentRepository(
                session,
                TenantContext(self.organization_a, self.user_a),
            ).list_recent()
            documents_b = DocumentRepository(
                session,
                TenantContext(self.organization_b, self.user_b),
            ).list_recent()
        self.assertEqual(len(documents_a), 1)
        self.assertEqual(len(documents_b), 1)
        self.assertNotEqual(documents_a[0].id, documents_b[0].id)

    def test_upload_scope_is_required_before_storage_or_database_work(self) -> None:
        self.set_identity(
            self.organization_a,
            self.subject_a,
            scopes=frozenset({"invoiceflow.read"}),
        )

        response = self.upload_pdf()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.storage.uploads, [])
        with self.database.transaction() as session:
            documents = DocumentRepository(
                session,
                TenantContext(self.organization_a, self.user_a),
            ).list_recent()
        self.assertEqual(documents, [])

    def test_spoofed_file_is_rejected_before_storage(self) -> None:
        response = self.client.post(
            "/v2/documents",
            headers=self.headers,
            files={"file": ("invoice.png", build_pdf(), "image/png")},
        )

        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.json()["detail"]["code"], "file_type_mismatch")
        self.assertEqual(self.storage.uploads, [])

    def test_storage_failure_rolls_back_database_and_attempts_cleanup(self) -> None:
        self.storage.fail_upload = True

        response = self.upload_pdf()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["code"], "storage_unavailable")
        self.assertEqual(len(self.storage.deletes), 1)
        with self.database.transaction() as session:
            documents = DocumentRepository(
                session,
                TenantContext(self.organization_a, self.user_a),
            ).list_recent()
        self.assertEqual(documents, [])

    def test_database_commit_failure_removes_uploaded_object(self) -> None:
        validator = UploadValidator(max_bytes=1024 * 1024, max_pdf_pages=3)
        upload = validator.validate(
            filename="invoice.pdf",
            declared_content_type="application/pdf",
            content=build_pdf(),
        )
        tenant = TenantContext(self.organization_a, self.user_a)
        session = self.database.session_factory()
        try:
            with patch.object(
                session,
                "commit",
                side_effect=SQLAlchemyError("private database detail"),
            ):
                with self.assertRaises(UploadPersistenceError) as context:
                    persist_quarantined_upload(
                        session=session,
                        tenant=tenant,
                        storage=self.storage,
                        upload=upload,
                        quarantine_prefix="quarantine",
                        validated_prefix="validated",
                    )
        finally:
            session.close()

        self.assertEqual(context.exception.code, "upload_persistence_failed")
        self.assertEqual(len(self.storage.deletes), 1)
        with self.database.transaction() as verification_session:
            documents = DocumentRepository(
                verification_session,
                TenantContext(self.organization_a, self.user_a),
            ).list_recent()
        self.assertEqual(documents, [])

    def test_cleanup_failure_does_not_replace_the_primary_upload_error(self) -> None:
        self.storage.fail_upload = True
        self.storage.fail_delete = True

        response = self.upload_pdf()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["code"], "storage_unavailable")
        self.assertEqual(len(self.storage.deletes), 1)


if __name__ == "__main__":
    unittest.main()
