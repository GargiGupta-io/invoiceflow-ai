from __future__ import annotations

import unittest
import uuid
from typing import Any, Mapping
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from api.v2 import router
from app.auth.claims import VerifiedIdentity
from app.auth.dependencies import get_database, get_token_verifier
from app.db import Base, DocumentStatus, Organization, User
from app.db.repositories import AuditEventRepository, DocumentRepository
from app.db.session import create_database
from app.db.tenant import TenantContext
from app.storage import StorageOperationError, StoredObject, build_document_keys, get_object_storage


class StaticTokenVerifier:
    def __init__(self, identity: VerifiedIdentity) -> None:
        self.identity = identity

    def verify(self, _token: str) -> VerifiedIdentity:
        return self.identity


class RecordingObjectStorage:
    def __init__(self) -> None:
        self.access_requests: list[dict[str, Any]] = []
        self.fail_access = False

    def upload_quarantined(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        metadata: Mapping[str, str] | None = None,
    ) -> StoredObject:
        raise AssertionError("Upload is not part of private document access.")

    def promote(self, *, source_key: str, destination_key: str) -> StoredObject:
        raise AssertionError("Promotion is not part of private document access.")

    def create_download_url(self, *, key: str, expires_in_seconds: int) -> str:
        self.access_requests.append(
            {"key": key, "expires_in_seconds": expires_in_seconds}
        )
        if self.fail_access:
            raise StorageOperationError("private provider detail")
        return "https://private.example.test/document?X-Amz-Signature=secret-token"

    def delete(self, *, key: str) -> None:
        raise AssertionError("Deletion is not part of private document access.")


class PrivateDocumentAccessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = create_database(database_url="sqlite://")
        Base.metadata.create_all(self.database.engine)
        self.organization_a = uuid.uuid4()
        self.organization_b = uuid.uuid4()
        self.user_a = uuid.uuid4()
        self.user_b = uuid.uuid4()
        self.subject_a = "cognito-access-user-a"
        self.subject_b = "cognito-access-user-b"
        self.tenant_a = TenantContext(self.organization_a, self.user_a)
        self.tenant_b = TenantContext(self.organization_b, self.user_b)

        with self.database.transaction() as session:
            session.add_all(
                [
                    Organization(id=self.organization_a, name="Organization A"),
                    Organization(id=self.organization_b, name="Organization B"),
                    User(
                        id=self.user_a,
                        organization_id=self.organization_a,
                        external_subject=self.subject_a,
                        email="access-a@example.com",
                    ),
                    User(
                        id=self.user_b,
                        organization_id=self.organization_b,
                        external_subject=self.subject_b,
                        email="access-b@example.com",
                    ),
                ]
            )

        self.document_a = self.create_document(self.tenant_a, validated=True)
        self.document_b = self.create_document(self.tenant_b, validated=True)
        self.quarantined_document = self.create_document(self.tenant_a, validated=False)
        self.storage = RecordingObjectStorage()
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[get_database] = lambda: self.database
        self.app.dependency_overrides[get_object_storage] = lambda: self.storage
        self.set_identity(self.organization_a, self.subject_a)
        self.client = TestClient(self.app)
        self.headers = {"Authorization": "Bearer valid-access-token"}

    def tearDown(self) -> None:
        self.database.dispose()

    def set_identity(
        self,
        organization_id: uuid.UUID,
        subject: str,
        *,
        scopes: frozenset[str] = frozenset({"invoiceflow.read"}),
    ) -> None:
        identity = VerifiedIdentity(
            subject=subject,
            organization_id=organization_id,
            username=None,
            scopes=scopes,
        )
        self.app.dependency_overrides[get_token_verifier] = lambda: StaticTokenVerifier(identity)

    def create_document(self, tenant: TenantContext, *, validated: bool):
        document_id = uuid.uuid4()
        keys = build_document_keys(
            organization_id=tenant.organization_id,
            document_id=document_id,
        )
        with self.database.transaction() as session:
            return DocumentRepository(session, tenant).create(
                document_id=document_id,
                original_filename="invoice.pdf",
                storage_key=keys.validated_key if validated else keys.quarantine_key,
                content_type="application/pdf",
                size_bytes=4096,
                page_count=2,
                status=DocumentStatus.VALIDATED if validated else DocumentStatus.QUARANTINED,
            )

    def request_access(self, document_id: uuid.UUID):
        return self.client.post(
            f"/v2/documents/{document_id}/access",
            headers=self.headers,
        )

    def test_owned_validated_document_returns_temporary_url_and_safe_audit(self) -> None:
        response = self.request_access(self.document_a.id)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["document_id"], str(self.document_a.id))
        self.assertEqual(payload["expires_in_seconds"], 300)
        self.assertIn("X-Amz-Signature", payload["url"])
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(self.storage.access_requests[0]["expires_in_seconds"], 300)

        with self.database.transaction() as session:
            events = AuditEventRepository(session, self.tenant_a).list_for_resource(
                "document",
                str(self.document_a.id),
            )
        self.assertEqual(events[0].action, "document.access_url_issued")
        self.assertEqual(events[0].request_id, payload["request_id"])
        self.assertNotIn("url", events[0].safe_metadata)
        self.assertNotIn("storage_key", events[0].safe_metadata)
        self.assertNotIn("original_filename", events[0].safe_metadata)

    def test_cross_tenant_document_returns_not_found_before_signing(self) -> None:
        response = self.request_access(self.document_b.id)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"]["code"], "resource_not_found")
        self.assertEqual(self.storage.access_requests, [])

    def test_quarantined_document_is_not_available_for_access(self) -> None:
        response = self.request_access(self.quarantined_document.id)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["code"], "document_not_ready")
        self.assertEqual(self.storage.access_requests, [])

    def test_read_scope_is_required_before_document_lookup(self) -> None:
        self.set_identity(
            self.organization_a,
            self.subject_a,
            scopes=frozenset({"invoiceflow.upload"}),
        )

        response = self.request_access(self.document_a.id)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.storage.access_requests, [])

    def test_storage_failure_returns_generic_error_without_audit_event(self) -> None:
        self.storage.fail_access = True

        response = self.request_access(self.document_a.id)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["code"], "storage_unavailable")
        self.assertNotIn("private provider detail", response.text)
        with self.database.transaction() as session:
            events = AuditEventRepository(session, self.tenant_a).list_for_resource(
                "document",
                str(self.document_a.id),
            )
        self.assertEqual(events, [])

    def test_audit_commit_failure_does_not_return_the_temporary_url(self) -> None:
        from api import v2

        session = self.database.session_factory()
        self.app.dependency_overrides[v2.get_db_session] = lambda: session
        try:
            with patch.object(
                session,
                "commit",
                side_effect=SQLAlchemyError("private database detail"),
            ):
                response = self.request_access(self.document_a.id)
        finally:
            session.close()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["code"], "access_audit_unavailable")
        self.assertNotIn("X-Amz-Signature", response.text)


if __name__ == "__main__":
    unittest.main()
