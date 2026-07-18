from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timedelta, timezone
from typing import Mapping

from sqlalchemy import select

from app.db import Base, DocumentStatus, JobStatus, Organization, ProcessingJob, User
from app.db.repositories import (
    AuditEventRepository,
    DocumentRepository,
    ProcessingJobRepository,
)
from app.db.session import create_database
from app.db.tenant import TenantContext
from app.retention import DocumentDeletionService, RetentionDeletionWorker
from app.storage import StorageOperationError, StoredObject, build_document_keys


class RetentionObjectStorage:
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
        raise AssertionError("Upload is not part of retention cleanup.")

    def promote(self, *, source_key: str, destination_key: str) -> StoredObject:
        raise AssertionError("Promotion is not part of retention cleanup.")

    def create_download_url(self, *, key: str, expires_in_seconds: int) -> str:
        raise AssertionError("Access is not part of retention cleanup.")

    def delete(self, *, key: str) -> None:
        self.deleted_keys.append(key)
        if self.fail_delete:
            raise StorageOperationError("private storage detail")


class RetentionDeletionWorkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = create_database(database_url="sqlite://")
        Base.metadata.create_all(self.database.engine)
        self.organization_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.tenant = TenantContext(self.organization_id, self.user_id)
        with self.database.transaction() as session:
            session.add(Organization(id=self.organization_id, name="Retention Org"))
            session.add(
                User(
                    id=self.user_id,
                    organization_id=self.organization_id,
                    external_subject="retention-user",
                    email="retention@example.com",
                )
            )
        self.storage = RetentionObjectStorage()
        service = DocumentDeletionService(
            storage=self.storage,
            quarantine_prefix="quarantine",
            validated_prefix="validated",
        )
        self.worker = RetentionDeletionWorker(
            database=self.database,
            deletion_service=service,
            batch_size=10,
        )
        self.now = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)

    def tearDown(self) -> None:
        self.database.dispose()

    def _create_document(
        self,
        *,
        retention_until: datetime,
        job_status: JobStatus = JobStatus.COMPLETED,
    ):
        document_id = uuid.uuid4()
        keys = build_document_keys(
            organization_id=self.organization_id,
            document_id=document_id,
        )
        with self.database.transaction() as session:
            document = DocumentRepository(session, self.tenant).create(
                document_id=document_id,
                original_filename="retention-invoice.pdf",
                storage_key=keys.validated_key,
                content_type="application/pdf",
                size_bytes=2048,
                status=DocumentStatus.COMPLETED,
                retention_until=retention_until,
            )
            job = ProcessingJobRepository(session, self.tenant).get_or_create(
                document_id=document.id,
                idempotency_key=f"retention-{document.id}",
            )
            job.status = job_status
            job.extraction_result = {"invoice_number": "RET-1"}
            job.evidence = [{"citation": "AP-001"}]
            return document

    def test_worker_deletes_only_expired_documents_with_system_audit(self) -> None:
        expired = self._create_document(retention_until=self.now - timedelta(seconds=1))
        future = self._create_document(retention_until=self.now + timedelta(days=1))

        result = self.worker.run_once(now=self.now)

        self.assertEqual(result.candidates, 1)
        self.assertEqual(result.deleted, 1)
        self.assertEqual(result.failed, 0)
        self.assertEqual(len(self.storage.deleted_keys), 2)
        with self.database.transaction() as session:
            expired_tombstone = DocumentRepository(
                session, self.tenant
            ).require_including_deleted(expired.id)
            future_document = DocumentRepository(session, self.tenant).require(
                future.id
            )
            events = AuditEventRepository(session, self.tenant).list_for_resource(
                "document", str(expired.id)
            )
        self.assertIsNotNone(expired_tombstone.deleted_at)
        self.assertIsNone(future_document.deleted_at)
        self.assertEqual(events[0].action, "document.deleted")
        self.assertIsNone(events[0].actor_id)
        self.assertEqual(
            events[0].safe_metadata["deletion_reason"],
            "retention_expired",
        )

    def test_active_expired_document_is_not_selected(self) -> None:
        active = self._create_document(
            retention_until=self.now - timedelta(days=1),
            job_status=JobStatus.PROCESSING,
        )
        with self.database.transaction() as session:
            document = DocumentRepository(session, self.tenant).require(active.id)
            document.status = DocumentStatus.PROCESSING

        result = self.worker.run_once(now=self.now)

        self.assertEqual(result.candidates, 0)
        self.assertEqual(result.deleted, 0)
        self.assertEqual(self.storage.deleted_keys, [])

    def test_storage_failure_rolls_back_retention_cleanup(self) -> None:
        expired = self._create_document(retention_until=self.now - timedelta(days=1))
        self.storage.fail_delete = True

        result = self.worker.run_once(now=self.now)

        self.assertEqual(result.failed, 1)
        with self.database.transaction() as session:
            document = DocumentRepository(session, self.tenant).require(expired.id)
            job = session.scalar(
                select(ProcessingJob).where(ProcessingJob.document_id == expired.id)
            )
        self.assertIsNone(document.deleted_at)
        self.assertIsNotNone(job)
        self.assertIsNotNone(job.extraction_result)

    def test_second_worker_run_does_not_repeat_deletion(self) -> None:
        self._create_document(retention_until=self.now - timedelta(days=1))

        first = self.worker.run_once(now=self.now)
        second = self.worker.run_once(now=self.now)

        self.assertEqual(first.deleted, 1)
        self.assertEqual(second.candidates, 0)
        self.assertEqual(len(self.storage.deleted_keys), 2)


if __name__ == "__main__":
    unittest.main()
