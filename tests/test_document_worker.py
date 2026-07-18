from __future__ import annotations

import unittest
import uuid
from typing import Any, Mapping

from app.db import Base, DocumentStatus, JobStatus, Organization, User
from app.db.repositories import AuditEventRepository, DocumentRepository, ProcessingJobRepository
from app.db.session import create_database
from app.db.tenant import TenantContext
from app.queue import (
    ProcessingMessage,
    QueueDispatchReceipt,
    QueueOperationError,
    ReceivedQueueMessage,
)
from app.storage import StorageOperationError, StoredObject, build_document_keys
from app.worker import DocumentWorker, ProcessedDocument, WorkerOutcome


class RecordingWorkerQueue:
    def __init__(self, received: ReceivedQueueMessage | None, events: list[str]) -> None:
        self.received = received
        self.events = events
        self.deleted: list[str] = []
        self.fail_delete = False

    def send(self, message: ProcessingMessage) -> QueueDispatchReceipt:
        raise AssertionError("Worker must not send processing messages.")

    def receive_one(self, *, wait_time_seconds: int, visibility_timeout_seconds: int):
        self.events.append("queue.receive")
        received, self.received = self.received, None
        return received

    def delete(self, *, receipt_handle: str) -> None:
        self.events.append("queue.delete")
        if self.fail_delete:
            raise QueueOperationError("Queue operation failed.")
        self.deleted.append(receipt_handle)


class RecordingWorkerStorage:
    def __init__(self, content: bytes, events: list[str]) -> None:
        self.content = content
        self.events = events
        self.promotions: list[tuple[str, str]] = []
        self.fail_read = False
        self.fail_promote = False

    def upload_quarantined(self, **_request):
        raise AssertionError("Worker must not upload a new object.")

    def read(self, *, key: str, max_bytes: int) -> bytes:
        self.events.append("storage.read")
        if self.fail_read:
            raise StorageOperationError("Storage operation failed.")
        if len(self.content) > max_bytes:
            raise StorageOperationError("Storage operation failed.")
        return self.content

    def promote(self, *, source_key: str, destination_key: str) -> StoredObject:
        self.events.append("storage.promote")
        if self.fail_promote:
            raise StorageOperationError("Storage operation failed.")
        self.promotions.append((source_key, destination_key))
        return StoredObject(bucket="private", key=destination_key)

    def create_download_url(self, **_request):
        raise AssertionError("Worker must not create access URLs.")

    def delete(self, **_request):
        raise AssertionError("Worker cleanup is not part of this step.")


class RecordingProcessor:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.calls: list[dict[str, Any]] = []
        self.error: Exception | None = None

    def process(self, *, filename: str, content: bytes, content_type: str) -> ProcessedDocument:
        self.events.append("processor.process")
        self.calls.append(
            {"filename": filename, "content": content, "content_type": content_type}
        )
        if self.error is not None:
            raise self.error
        return ProcessedDocument(
            result={
                "workflow_result": {"workflow_type": "accounts_payable"},
                "route": {"workflow_type": "accounts_payable"},
            },
            evidence=[{"source_id": "AP-APPROVAL-001", "excerpt": "Policy evidence"}],
        )


class DocumentWorkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = create_database(database_url="sqlite://")
        Base.metadata.create_all(self.database.engine)
        self.organization_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.tenant = TenantContext(self.organization_id, self.user_id)
        self.document_id = uuid.uuid4()
        self.keys = build_document_keys(
            organization_id=self.organization_id,
            document_id=self.document_id,
        )
        with self.database.transaction() as session:
            session.add(Organization(id=self.organization_id, name="Worker Organization"))
            session.add(
                User(
                    id=self.user_id,
                    organization_id=self.organization_id,
                    external_subject="worker-requester",
                    email="worker@example.com",
                )
            )
        with self.database.transaction() as session:
            DocumentRepository(session, self.tenant).create(
                document_id=self.document_id,
                original_filename="invoice.pdf",
                storage_key=self.keys.quarantine_key,
                content_type="application/pdf",
                size_bytes=1024,
                page_count=1,
                status=DocumentStatus.QUEUED,
            )
            self.job = ProcessingJobRepository(session, self.tenant).get_or_create(
                document_id=self.document_id,
                idempotency_key="worker-test-job",
            )

        self.message = ProcessingMessage(
            job_id=self.job.id,
            document_id=self.document_id,
            organization_id=self.organization_id,
            request_id=uuid.uuid4(),
        )
        self.events: list[str] = []
        self.queue = RecordingWorkerQueue(self.received(self.message.to_body()), self.events)
        self.storage = RecordingWorkerStorage(b"invoice bytes", self.events)
        self.processor = RecordingProcessor(self.events)

    def tearDown(self) -> None:
        self.database.dispose()

    def received(self, body: str) -> ReceivedQueueMessage:
        return ReceivedQueueMessage(
            message_id="sqs-received-1",
            receipt_handle="receipt-handle-1",
            body=body,
            receive_count=1,
        )

    def worker(self) -> DocumentWorker:
        return DocumentWorker(
            database=self.database,
            queue=self.queue,
            storage=self.storage,
            processor=self.processor,
            quarantine_prefix="quarantine",
            validated_prefix="validated",
            max_document_bytes=10 * 1024 * 1024,
            wait_time_seconds=20,
            visibility_timeout_seconds=120,
        )

    def test_success_persists_result_before_deleting_message(self) -> None:
        result = self.worker().run_once()

        self.assertEqual(result.outcome, WorkerOutcome.COMPLETED)
        self.assertEqual(self.queue.deleted, ["receipt-handle-1"])
        self.assertEqual(
            self.events,
            [
                "queue.receive",
                "storage.read",
                "processor.process",
                "storage.promote",
                "queue.delete",
            ],
        )
        with self.database.transaction() as session:
            job = ProcessingJobRepository(session, self.tenant).get(self.job.id)
            document = DocumentRepository(session, self.tenant).require(self.document_id)
            audit = AuditEventRepository(session, self.tenant).list_for_resource(
                "document", str(self.document_id)
            )
        assert job is not None
        self.assertEqual(job.status, JobStatus.COMPLETED)
        self.assertEqual(job.attempt_count, 1)
        self.assertEqual(job.extraction_result["workflow_result"]["workflow_type"], "accounts_payable")
        self.assertEqual(job.evidence[0]["source_id"], "AP-APPROVAL-001")
        self.assertEqual(document.status, DocumentStatus.COMPLETED)
        self.assertEqual(document.storage_key, self.keys.validated_key)
        self.assertEqual(
            {event.action for event in audit},
            {"document.processing_started", "document.processing_completed"},
        )

    def test_completed_duplicate_is_acknowledged_without_processing(self) -> None:
        self.assertEqual(self.worker().run_once().outcome, WorkerOutcome.COMPLETED)
        self.events.clear()
        self.queue.deleted.clear()
        self.queue.received = self.received(self.message.to_body())

        result = self.worker().run_once()

        self.assertEqual(result.outcome, WorkerOutcome.ALREADY_COMPLETED)
        self.assertEqual(self.events, ["queue.receive", "queue.delete"])
        self.assertEqual(len(self.processor.calls), 1)

    def test_processing_duplicate_is_left_unacknowledged(self) -> None:
        with self.database.transaction() as session:
            claim = ProcessingJobRepository(session, self.tenant).claim(
                job_id=self.job.id,
                document_id=self.document_id,
            )
            DocumentRepository(session, self.tenant).mark_processing(self.document_id)
            self.assertEqual(claim.job.status, JobStatus.PROCESSING)

        result = self.worker().run_once()

        self.assertEqual(result.outcome, WorkerOutcome.IN_PROGRESS)
        self.assertEqual(self.queue.deleted, [])
        self.assertEqual(self.processor.calls, [])

    def test_invalid_or_unknown_message_is_not_acknowledged(self) -> None:
        self.queue.received = self.received("not-json")
        invalid = self.worker().run_once()
        self.assertEqual(invalid.outcome, WorkerOutcome.INVALID_MESSAGE)
        self.assertEqual(self.queue.deleted, [])

        unknown = ProcessingMessage(
            job_id=uuid.uuid4(),
            document_id=self.document_id,
            organization_id=self.organization_id,
            request_id=uuid.uuid4(),
        )
        self.queue.received = self.received(unknown.to_body())
        result = self.worker().run_once()
        self.assertEqual(result.outcome, WorkerOutcome.UNKNOWN_JOB)
        self.assertEqual(self.queue.deleted, [])

    def test_workflow_failure_is_saved_and_message_is_not_deleted(self) -> None:
        self.processor.error = RuntimeError("sensitive invoice content")

        result = self.worker().run_once()

        self.assertEqual(result.outcome, WorkerOutcome.FAILED)
        self.assertEqual(self.queue.deleted, [])
        with self.database.transaction() as session:
            job = ProcessingJobRepository(session, self.tenant).get(self.job.id)
            document = DocumentRepository(session, self.tenant).require(self.document_id)
            audit = AuditEventRepository(session, self.tenant).list_for_resource(
                "document", str(self.document_id)
            )
        assert job is not None
        self.assertEqual(job.status, JobStatus.FAILED)
        self.assertEqual(job.error_code, "document_processing_failed")
        self.assertNotIn("sensitive invoice", str(job.error_code))
        self.assertEqual(document.status, DocumentStatus.FAILED)
        self.assertEqual(audit[0].action, "document.processing_failed")

    def test_delete_failure_leaves_completed_job_for_safe_redelivery(self) -> None:
        self.queue.fail_delete = True

        result = self.worker().run_once()

        self.assertEqual(result.outcome, WorkerOutcome.ACK_FAILED)
        with self.database.transaction() as session:
            job = ProcessingJobRepository(session, self.tenant).get(self.job.id)
        assert job is not None
        self.assertEqual(job.status, JobStatus.COMPLETED)


if __name__ == "__main__":
    unittest.main()
