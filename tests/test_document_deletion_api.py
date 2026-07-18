from __future__ import annotations

import unittest
import uuid
from typing import Mapping

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from api.v2 import router
from app.auth.claims import VerifiedIdentity
from app.auth.dependencies import get_database, get_token_verifier
from app.db import (
    Base,
    DocumentStatus,
    JobStatus,
    Organization,
    ProcessingJob,
    ReviewAction,
    ReviewDecision,
    User,
)
from app.db.repositories import (
    AuditEventRepository,
    DocumentRepository,
    ProcessingJobRepository,
    ReviewDecisionRepository,
)
from app.db.session import create_database
from app.db.tenant import TenantContext
from app.storage import (
    StorageOperationError,
    StoredObject,
    build_document_keys,
    get_object_storage,
)


class StaticTokenVerifier:
    def __init__(self, identity: VerifiedIdentity) -> None:
        self.identity = identity

    def verify(self, _token: str) -> VerifiedIdentity:
        return self.identity


class DeletionObjectStorage:
    def __init__(self) -> None:
        self.deleted_keys: list[str] = []
        self.fail_delete = False

    def upload_quarantined(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        metadata: Mapping[str, str] | None = None,
    ) -> StoredObject:
        raise AssertionError("Upload is not part of document deletion.")

    def promote(self, *, source_key: str, destination_key: str) -> StoredObject:
        raise AssertionError("Promotion is not part of document deletion.")

    def create_download_url(self, *, key: str, expires_in_seconds: int) -> str:
        raise AssertionError("Access is not part of document deletion.")

    def delete(self, *, key: str) -> None:
        self.deleted_keys.append(key)
        if self.fail_delete:
            raise StorageOperationError("private storage detail")


class DocumentDeletionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = create_database(database_url="sqlite://")
        Base.metadata.create_all(self.database.engine)
        self.organization_a = uuid.uuid4()
        self.organization_b = uuid.uuid4()
        self.user_a = uuid.uuid4()
        self.user_b = uuid.uuid4()
        self.subject_a = "delete-user-a"
        self.subject_b = "delete-user-b"
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
                        email="delete-a@example.com",
                    ),
                    User(
                        id=self.user_b,
                        organization_id=self.organization_b,
                        external_subject=self.subject_b,
                        email="delete-b@example.com",
                    ),
                ]
            )

        self.document_a = self._create_completed_case(self.tenant_a, "a")
        self.document_b = self._create_completed_case(self.tenant_b, "b")
        self.storage = DeletionObjectStorage()
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[get_database] = lambda: self.database
        self.app.dependency_overrides[get_object_storage] = lambda: self.storage
        self._set_identity(
            self.organization_a,
            self.subject_a,
            scopes=frozenset({"invoiceflow.read", "invoiceflow.delete"}),
        )
        self.client = TestClient(self.app)
        self.headers = {"Authorization": "Bearer valid-delete-token"}

    def tearDown(self) -> None:
        self.database.dispose()

    def _set_identity(
        self,
        organization_id: uuid.UUID,
        subject: str,
        *,
        scopes: frozenset[str],
    ) -> None:
        identity = VerifiedIdentity(
            subject=subject,
            organization_id=organization_id,
            username=None,
            scopes=scopes,
        )
        self.app.dependency_overrides[get_token_verifier] = lambda: StaticTokenVerifier(
            identity
        )

    def _create_completed_case(self, tenant: TenantContext, suffix: str):
        document_id = uuid.uuid4()
        keys = build_document_keys(
            organization_id=tenant.organization_id,
            document_id=document_id,
        )
        with self.database.transaction() as session:
            document = DocumentRepository(session, tenant).create(
                document_id=document_id,
                original_filename=f"invoice-{suffix}.pdf",
                storage_key=keys.validated_key,
                content_type="application/pdf",
                size_bytes=4096,
                page_count=2,
                status=DocumentStatus.COMPLETED,
            )
            job = ProcessingJobRepository(session, tenant).get_or_create(
                document_id=document.id,
                idempotency_key=f"delete-{suffix}",
            )
            job.status = JobStatus.COMPLETED
            job.extraction_result = {"invoice_number": f"INV-{suffix}"}
            job.evidence = [{"citation": "AP-001"}]
            ReviewDecisionRepository(session, tenant).create(
                document_id=document.id,
                processing_job_id=job.id,
                action=ReviewAction.APPROVED,
                reason="Policy checks passed.",
                reviewer_note="Sensitive reviewer note.",
                decision_payload={"private": "decision data"},
            )
            AuditEventRepository(session, tenant).append(
                action="document.uploaded",
                resource_type="document",
                resource_id=str(document.id),
                request_id=str(uuid.uuid4()),
                safe_metadata={"content_type": "application/pdf"},
            )
            return document

    def _delete(self, document_id: uuid.UUID):
        return self.client.delete(
            f"/v2/documents/{document_id}",
            headers=self.headers,
        )

    def test_owned_document_deletion_removes_private_data_and_keeps_safe_audit(
        self,
    ) -> None:
        response = self._delete(self.document_a.id)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["already_deleted"])
        expected_keys = build_document_keys(
            organization_id=self.organization_a,
            document_id=self.document_a.id,
        )
        self.assertEqual(
            self.storage.deleted_keys,
            [expected_keys.quarantine_key, expected_keys.validated_key],
        )
        self.assertEqual(
            self.client.get(
                f"/v2/documents/{self.document_a.id}", headers=self.headers
            ).status_code,
            404,
        )

        audit_response = self.client.get(
            f"/v2/documents/{self.document_a.id}/audit",
            headers=self.headers,
        )
        self.assertEqual(audit_response.status_code, 200)
        deletion_event = audit_response.json()[0]
        self.assertEqual(deletion_event["action"], "document.deleted")
        self.assertEqual(
            deletion_event["safe_metadata"]["deletion_reason"], "user_requested"
        )
        self.assertNotIn("storage_key", deletion_event["safe_metadata"])
        self.assertNotIn("original_filename", deletion_event["safe_metadata"])

        with self.database.transaction() as session:
            tombstone = DocumentRepository(
                session, self.tenant_a
            ).require_including_deleted(self.document_a.id)
            job_count = session.scalar(
                select(func.count())
                .select_from(ProcessingJob)
                .where(ProcessingJob.document_id == self.document_a.id)
            )
            review_count = session.scalar(
                select(func.count())
                .select_from(ReviewDecision)
                .where(ReviewDecision.document_id == self.document_a.id)
            )
        self.assertEqual(tombstone.status, DocumentStatus.DELETED)
        self.assertEqual(tombstone.original_filename, "[deleted]")
        self.assertIsNotNone(tombstone.deleted_at)
        self.assertEqual(job_count, 0)
        self.assertEqual(review_count, 0)

    def test_repeated_deletion_returns_same_tombstone_without_more_storage_calls(
        self,
    ) -> None:
        first = self._delete(self.document_a.id)
        second = self._delete(self.document_a.id)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["already_deleted"])
        self.assertEqual(second.json()["deleted_at"], first.json()["deleted_at"])
        self.assertEqual(len(self.storage.deleted_keys), 2)
        audit = self.client.get(
            f"/v2/documents/{self.document_a.id}/audit", headers=self.headers
        ).json()
        self.assertEqual(
            len([event for event in audit if event["action"] == "document.deleted"]),
            1,
        )

    def test_cross_tenant_deletion_returns_not_found_before_storage(self) -> None:
        response = self._delete(self.document_b.id)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"]["code"], "resource_not_found")
        self.assertEqual(self.storage.deleted_keys, [])

    def test_delete_scope_is_required_before_document_lookup(self) -> None:
        self._set_identity(
            self.organization_a,
            self.subject_a,
            scopes=frozenset({"invoiceflow.read"}),
        )

        response = self._delete(self.document_a.id)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.storage.deleted_keys, [])

    def test_storage_failure_keeps_database_case_available(self) -> None:
        self.storage.fail_delete = True

        response = self._delete(self.document_a.id)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["code"], "storage_unavailable")
        self.assertNotIn("private storage detail", response.text)
        detail = self.client.get(
            f"/v2/documents/{self.document_a.id}", headers=self.headers
        )
        self.assertEqual(detail.status_code, 200)

    def test_active_processing_job_blocks_deletion(self) -> None:
        active_document = self._create_completed_case(self.tenant_a, "active")
        with self.database.transaction() as session:
            job = session.scalar(
                select(ProcessingJob).where(
                    ProcessingJob.document_id == active_document.id
                )
            )
            job.status = JobStatus.PROCESSING

        response = self._delete(active_document.id)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"]["code"],
            "document_processing_active",
        )
        self.assertEqual(self.storage.deleted_keys, [])


if __name__ == "__main__":
    unittest.main()
