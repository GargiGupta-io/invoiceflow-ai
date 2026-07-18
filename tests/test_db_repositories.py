from __future__ import annotations

import uuid
import unittest

from app.db import Base, Organization, ReviewAction, User
from app.db.repositories import (
    AuditEventRepository,
    DocumentRepository,
    IdempotencyConflict,
    ProcessingJobRepository,
    ReviewDecisionRepository,
    TenantResourceNotFound,
)
from app.db.session import create_database
from app.db.tenant import TenantContext


class DatabaseRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = create_database(database_url="sqlite://")
        Base.metadata.create_all(self.database.engine)
        self.organization_a = uuid.uuid4()
        self.organization_b = uuid.uuid4()
        self.user_a = uuid.uuid4()
        self.user_b = uuid.uuid4()
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
                        external_subject="user-a",
                        email="user-a@example.com",
                    ),
                    User(
                        id=self.user_b,
                        organization_id=self.organization_b,
                        external_subject="user-b",
                        email="user-b@example.com",
                    ),
                ]
            )

    def tearDown(self) -> None:
        self.database.dispose()

    def _create_document(self, tenant: TenantContext, suffix: str):
        with self.database.transaction() as session:
            return DocumentRepository(session, tenant).create(
                original_filename=f"invoice-{suffix}.pdf",
                storage_key=f"quarantine/{tenant.organization_id}/invoice-{suffix}.pdf",
                content_type="application/pdf",
                size_bytes=2048,
                page_count=2,
            )

    def test_transaction_rolls_back_after_exception(self) -> None:
        rolled_back_id = uuid.uuid4()

        with self.assertRaises(RuntimeError):
            with self.database.transaction() as session:
                session.add(Organization(id=rolled_back_id, name="Rolled Back"))
                raise RuntimeError("force rollback")

        with self.database.transaction() as session:
            self.assertIsNone(session.get(Organization, rolled_back_id))

    def test_document_reads_do_not_cross_tenant_boundary(self) -> None:
        document = self._create_document(self.tenant_a, "tenant-a")

        with self.database.transaction() as session:
            self.assertEqual(DocumentRepository(session, self.tenant_a).require(document.id).id, document.id)
            with self.assertRaises(TenantResourceNotFound):
                DocumentRepository(session, self.tenant_b).require(document.id)

    def test_recent_documents_only_include_current_tenant(self) -> None:
        document_a = self._create_document(self.tenant_a, "a")
        self._create_document(self.tenant_b, "b")

        with self.database.transaction() as session:
            documents = DocumentRepository(session, self.tenant_a).list_recent()

        self.assertEqual([document.id for document in documents], [document_a.id])

    def test_idempotency_keys_are_scoped_to_organization(self) -> None:
        document_a = self._create_document(self.tenant_a, "job-a")
        document_b = self._create_document(self.tenant_b, "job-b")

        with self.database.transaction() as session:
            jobs_a = ProcessingJobRepository(session, self.tenant_a)
            first = jobs_a.get_or_create(
                document_id=document_a.id,
                idempotency_key="same-request",
            )
            repeated = jobs_a.get_or_create(
                document_id=document_a.id,
                idempotency_key="same-request",
            )
            job_b = ProcessingJobRepository(session, self.tenant_b).get_or_create(
                document_id=document_b.id,
                idempotency_key="same-request",
            )

        self.assertEqual(first.id, repeated.id)
        self.assertNotEqual(first.id, job_b.id)

    def test_idempotency_key_cannot_be_reused_for_another_document(self) -> None:
        first_document = self._create_document(self.tenant_a, "first-idempotent")
        second_document = self._create_document(self.tenant_a, "second-idempotent")

        with self.database.transaction() as session:
            jobs = ProcessingJobRepository(session, self.tenant_a)
            jobs.get_or_create(
                document_id=first_document.id,
                idempotency_key="single-operation",
            )

            with self.assertRaises(IdempotencyConflict):
                jobs.get_or_create(
                    document_id=second_document.id,
                    idempotency_key="single-operation",
                )

    def test_review_requires_matching_owned_document_and_job(self) -> None:
        document_a = self._create_document(self.tenant_a, "review-a")
        document_b = self._create_document(self.tenant_a, "review-b")

        with self.database.transaction() as session:
            job = ProcessingJobRepository(session, self.tenant_a).get_or_create(
                document_id=document_a.id,
                idempotency_key="review-job",
            )
            reviews = ReviewDecisionRepository(session, self.tenant_a)
            review = reviews.create(
                document_id=document_a.id,
                processing_job_id=job.id,
                action=ReviewAction.APPROVED,
                reason="Policy checks passed.",
            )
            self.assertEqual(review.organization_id, self.organization_a)

            with self.assertRaises(TenantResourceNotFound):
                reviews.create(
                    document_id=document_b.id,
                    processing_job_id=job.id,
                    action=ReviewAction.REJECTED,
                    reason="Mismatched case.",
                )

    def test_audit_reads_are_tenant_filtered_and_append_only(self) -> None:
        with self.database.transaction() as session:
            audit_a = AuditEventRepository(session, self.tenant_a)
            event = audit_a.append(
                action="document.uploaded",
                resource_type="document",
                resource_id="document-123",
                request_id="request-123",
                safe_metadata={"content_type": "application/pdf"},
            )
            self.assertEqual(event.organization_id, self.organization_a)
            self.assertFalse(hasattr(audit_a, "update"))
            self.assertFalse(hasattr(audit_a, "delete"))

        with self.database.transaction() as session:
            self.assertEqual(
                len(
                    AuditEventRepository(session, self.tenant_a).list_for_resource(
                        "document", "document-123"
                    )
                ),
                1,
            )
            self.assertEqual(
                AuditEventRepository(session, self.tenant_b).list_for_resource(
                    "document", "document-123"
                ),
                [],
            )


if __name__ == "__main__":
    unittest.main()
