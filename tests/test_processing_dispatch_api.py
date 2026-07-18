from __future__ import annotations

import unittest
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v2 import router
from app.auth.claims import VerifiedIdentity
from app.auth.dependencies import get_database, get_token_verifier
from app.db import Base, DocumentStatus, Organization, User
from app.db.repositories import AuditEventRepository, DocumentRepository, ProcessingJobRepository
from app.db.session import create_database
from app.db.tenant import TenantContext
from app.queue import (
    ProcessingMessage,
    QueueDispatchReceipt,
    QueueOperationError,
    get_processing_queue,
)
from app.storage import build_document_keys


class StaticTokenVerifier:
    def __init__(self, identity: VerifiedIdentity) -> None:
        self.identity = identity

    def verify(self, _token: str) -> VerifiedIdentity:
        return self.identity


class RecordingProcessingQueue:
    def __init__(self) -> None:
        self.messages: list[ProcessingMessage] = []
        self.fail = False

    def send(self, message: ProcessingMessage) -> QueueDispatchReceipt:
        self.messages.append(message)
        if self.fail:
            raise QueueOperationError("Queue operation failed.")
        return QueueDispatchReceipt(message_id=f"message-{len(self.messages)}")


class ProcessingDispatchApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = create_database(database_url="sqlite://")
        Base.metadata.create_all(self.database.engine)
        self.organization_a = uuid.uuid4()
        self.organization_b = uuid.uuid4()
        self.user_a = uuid.uuid4()
        self.user_b = uuid.uuid4()
        self.subject_a = "cognito-process-user-a"
        self.subject_b = "cognito-process-user-b"
        with self.database.transaction() as session:
            session.add_all(
                [
                    Organization(id=self.organization_a, name="Organization A"),
                    Organization(id=self.organization_b, name="Organization B"),
                    User(
                        id=self.user_a,
                        organization_id=self.organization_a,
                        external_subject=self.subject_a,
                        email="processor-a@example.com",
                    ),
                    User(
                        id=self.user_b,
                        organization_id=self.organization_b,
                        external_subject=self.subject_b,
                        email="processor-b@example.com",
                    ),
                ]
            )

        self.queue = RecordingProcessingQueue()
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[get_database] = lambda: self.database
        self.app.dependency_overrides[get_processing_queue] = lambda: self.queue
        self.set_identity(self.organization_a, self.subject_a)
        self.client = TestClient(self.app)
        self.authorization = {"Authorization": "Bearer valid-process-token"}

    def tearDown(self) -> None:
        self.database.dispose()

    def set_identity(
        self,
        organization_id: uuid.UUID,
        subject: str,
        *,
        scopes: frozenset[str] = frozenset({"invoiceflow.process"}),
    ) -> None:
        identity = VerifiedIdentity(
            subject=subject,
            organization_id=organization_id,
            username=None,
            scopes=scopes,
        )
        self.app.dependency_overrides[get_token_verifier] = lambda: StaticTokenVerifier(identity)

    def create_document(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        status: DocumentStatus = DocumentStatus.QUARANTINED,
    ):
        tenant = TenantContext(organization_id, user_id)
        document_id = uuid.uuid4()
        keys = build_document_keys(
            organization_id=organization_id,
            document_id=document_id,
            quarantine_prefix="quarantine",
            validated_prefix="validated",
        )
        storage_key = (
            keys.quarantine_key
            if status is DocumentStatus.QUARANTINED
            else keys.validated_key
        )
        with self.database.transaction() as session:
            return DocumentRepository(session, tenant).create(
                document_id=document_id,
                original_filename="invoice.pdf",
                storage_key=storage_key,
                content_type="application/pdf",
                size_bytes=1024,
                page_count=1,
                status=status,
            )

    def dispatch(self, document_id: uuid.UUID, idempotency_key: str):
        return self.client.post(
            f"/v2/documents/{document_id}/processing-jobs",
            headers={**self.authorization, "Idempotency-Key": idempotency_key},
        )

    def test_dispatch_creates_one_tenant_job_and_safe_audit_events(self) -> None:
        document = self.create_document(self.organization_a, self.user_a)

        response = self.dispatch(document.id, "upload-a-001")

        self.assertEqual(response.status_code, 202)
        payload = response.json()
        self.assertFalse(payload["reused_job"])
        self.assertEqual(payload["dispatch_state"], "sent")
        self.assertEqual(payload["processing_job"]["document_id"], str(document.id))
        self.assertEqual(payload["processing_job"]["status"], "queued")
        self.assertNotIn("queue_message_id", payload)
        self.assertNotIn("idempotency_key", payload["processing_job"])

        message = self.queue.messages[0]
        self.assertEqual(message.document_id, document.id)
        self.assertEqual(message.organization_id, self.organization_a)
        self.assertEqual(message.job_id, uuid.UUID(payload["processing_job"]["id"]))
        self.assertEqual(message.request_id, uuid.UUID(payload["request_id"]))

        tenant = TenantContext(self.organization_a, self.user_a)
        with self.database.transaction() as session:
            saved_document = DocumentRepository(session, tenant).require(document.id)
            jobs = ProcessingJobRepository(session, tenant).list_for_document(document.id)
            events = AuditEventRepository(session, tenant).list_for_resource(
                "document", str(document.id)
            )
        self.assertEqual(saved_document.status, DocumentStatus.QUEUED)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(
            {event.action for event in events},
            {"document.processing_requested", "document.processing_dispatched"},
        )
        for event in events:
            metadata = event.safe_metadata
            self.assertNotIn("idempotency_key", metadata)
            self.assertNotIn("queue_url", metadata)
            self.assertNotIn("storage_key", metadata)

    def test_same_idempotency_key_reuses_job_and_can_redeliver(self) -> None:
        document = self.create_document(self.organization_a, self.user_a)

        first = self.dispatch(document.id, "retry-safe-001")
        second = self.dispatch(document.id, "retry-safe-001")

        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 202)
        self.assertFalse(first.json()["reused_job"])
        self.assertTrue(second.json()["reused_job"])
        self.assertEqual(
            first.json()["processing_job"]["id"],
            second.json()["processing_job"]["id"],
        )
        self.assertEqual(len(self.queue.messages), 2)
        self.assertEqual(self.queue.messages[0].job_id, self.queue.messages[1].job_id)

        tenant = TenantContext(self.organization_a, self.user_a)
        with self.database.transaction() as session:
            jobs = ProcessingJobRepository(session, tenant).list_for_document(document.id)
            events = AuditEventRepository(session, tenant).list_for_resource(
                "document", str(document.id)
            )
        self.assertEqual(len(jobs), 1)
        self.assertEqual(
            [event.action for event in events].count("document.processing_requested"),
            1,
        )
        self.assertEqual(
            [event.action for event in events].count("document.processing_dispatched"),
            2,
        )

    def test_idempotency_key_cannot_be_moved_to_another_document(self) -> None:
        first_document = self.create_document(self.organization_a, self.user_a)
        second_document = self.create_document(self.organization_a, self.user_a)
        self.assertEqual(self.dispatch(first_document.id, "single-operation").status_code, 202)

        response = self.dispatch(second_document.id, "single-operation")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["code"], "idempotency_conflict")
        self.assertEqual(len(self.queue.messages), 1)

    def test_cross_tenant_document_is_hidden_before_queue_dispatch(self) -> None:
        document = self.create_document(self.organization_a, self.user_a)
        self.set_identity(self.organization_b, self.subject_b)

        response = self.dispatch(document.id, "cross-tenant-attempt")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.queue.messages, [])

    def test_process_scope_is_required_before_queue_dispatch(self) -> None:
        document = self.create_document(self.organization_a, self.user_a)
        self.set_identity(
            self.organization_a,
            self.subject_a,
            scopes=frozenset({"invoiceflow.read"}),
        )

        response = self.dispatch(document.id, "missing-process-scope")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.queue.messages, [])

    def test_invalid_idempotency_key_is_rejected_before_queue_dispatch(self) -> None:
        document = self.create_document(self.organization_a, self.user_a)

        response = self.dispatch(document.id, "contains spaces")

        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.queue.messages, [])

    def test_non_quarantine_document_cannot_create_a_new_job(self) -> None:
        document = self.create_document(
            self.organization_a,
            self.user_a,
            status=DocumentStatus.VALIDATED,
        )

        response = self.dispatch(document.id, "already-validated")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["code"], "document_not_ready")
        self.assertEqual(self.queue.messages, [])

    def test_queue_failure_keeps_one_job_for_same_key_retry(self) -> None:
        document = self.create_document(self.organization_a, self.user_a)
        self.queue.fail = True

        failed = self.dispatch(document.id, "queue-recovery-001")

        self.assertEqual(failed.status_code, 503)
        self.assertEqual(
            failed.json()["detail"]["code"],
            "processing_queue_unavailable",
        )
        self.queue.fail = False
        retried = self.dispatch(document.id, "queue-recovery-001")
        self.assertEqual(retried.status_code, 202)
        self.assertTrue(retried.json()["reused_job"])

        tenant = TenantContext(self.organization_a, self.user_a)
        with self.database.transaction() as session:
            jobs = ProcessingJobRepository(session, tenant).list_for_document(document.id)
        self.assertEqual(len(jobs), 1)


if __name__ == "__main__":
    unittest.main()
