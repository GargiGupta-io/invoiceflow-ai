from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.exc import SQLAlchemyError

from app.db.repositories import (
    AuditEventRepository,
    DocumentRepository,
    JobClaimState,
    ProcessingJobRepository,
    TenantResourceNotFound,
    resolve_worker_tenant,
)
from app.db.session import Database
from app.queue import (
    ProcessingMessage,
    ProcessingQueue,
    QueueMessageValidationError,
    QueueOperationError,
    ReceivedQueueMessage,
)
from app.storage import ObjectStorage, StorageOperationError, build_document_keys
from app.worker.processor import DocumentProcessor, ProcessedDocument


class WorkerOutcome(str, Enum):
    NO_MESSAGE = "no_message"
    COMPLETED = "completed"
    ALREADY_COMPLETED = "already_completed"
    IN_PROGRESS = "in_progress"
    INVALID_MESSAGE = "invalid_message"
    UNKNOWN_JOB = "unknown_job"
    FAILED = "failed"
    ACK_FAILED = "ack_failed"


@dataclass(frozen=True)
class WorkerRunResult:
    outcome: WorkerOutcome
    message_id: str | None = None
    job_id: uuid.UUID | None = None
    receive_count: int | None = None


class WorkerExecutionError(RuntimeError):
    """A safe worker failure that excludes document and provider details."""


class DocumentWorker:
    def __init__(
        self,
        *,
        database: Database,
        queue: ProcessingQueue,
        storage: ObjectStorage,
        processor: DocumentProcessor,
        quarantine_prefix: str,
        validated_prefix: str,
        max_document_bytes: int,
        wait_time_seconds: int,
        visibility_timeout_seconds: int,
    ) -> None:
        self.database = database
        self.queue = queue
        self.storage = storage
        self.processor = processor
        self.quarantine_prefix = quarantine_prefix
        self.validated_prefix = validated_prefix
        self.max_document_bytes = max_document_bytes
        self.wait_time_seconds = wait_time_seconds
        self.visibility_timeout_seconds = visibility_timeout_seconds

    def run_once(self) -> WorkerRunResult:
        try:
            received = self.queue.receive_one(
                wait_time_seconds=self.wait_time_seconds,
                visibility_timeout_seconds=self.visibility_timeout_seconds,
            )
        except QueueOperationError:
            raise WorkerExecutionError("The processing queue could not be read.") from None
        if received is None:
            return WorkerRunResult(outcome=WorkerOutcome.NO_MESSAGE)

        try:
            message = ProcessingMessage.from_body(received.body)
        except QueueMessageValidationError:
            return self._result(WorkerOutcome.INVALID_MESSAGE, received)

        try:
            claim_state = self._claim(message=message, received=received)
        except TenantResourceNotFound:
            return self._result(WorkerOutcome.UNKNOWN_JOB, received, message.job_id)
        if claim_state == JobClaimState.COMPLETED:
            return self._acknowledge(
                outcome=WorkerOutcome.ALREADY_COMPLETED,
                received=received,
                job_id=message.job_id,
            )
        if claim_state == JobClaimState.UNAVAILABLE:
            return self._result(WorkerOutcome.IN_PROGRESS, received, message.job_id)

        keys = build_document_keys(
            organization_id=message.organization_id,
            document_id=message.document_id,
            quarantine_prefix=self.quarantine_prefix,
            validated_prefix=self.validated_prefix,
        )
        promoted = False
        try:
            document = self._load_document(message)
            content = self.storage.read(
                key=keys.quarantine_key,
                max_bytes=self.max_document_bytes,
            )
            processed = self.processor.process(
                filename=document.original_filename,
                content=content,
                content_type=document.content_type,
            )
            self.storage.promote(
                source_key=keys.quarantine_key,
                destination_key=keys.validated_key,
            )
            promoted = True
            self._complete(
                message=message,
                received=received,
                processed=processed,
                validated_key=keys.validated_key,
            )
        except StorageOperationError:
            self._record_failure(
                message=message,
                received=received,
                error_code="storage_processing_failed",
                error_category="storage",
                promoted=promoted,
                validated_key=keys.validated_key,
            )
            return self._result(WorkerOutcome.FAILED, received, message.job_id)
        except (SQLAlchemyError, TenantResourceNotFound, ValueError):
            self._record_failure(
                message=message,
                received=received,
                error_code="processing_state_failed",
                error_category="persistence",
                promoted=promoted,
                validated_key=keys.validated_key,
            )
            return self._result(WorkerOutcome.FAILED, received, message.job_id)
        except Exception:
            self._record_failure(
                message=message,
                received=received,
                error_code="document_processing_failed",
                error_category="workflow",
                promoted=promoted,
                validated_key=keys.validated_key,
            )
            return self._result(WorkerOutcome.FAILED, received, message.job_id)

        return self._acknowledge(
            outcome=WorkerOutcome.COMPLETED,
            received=received,
            job_id=message.job_id,
        )

    def _claim(
        self,
        *,
        message: ProcessingMessage,
        received: ReceivedQueueMessage,
    ) -> JobClaimState:
        try:
            with self.database.transaction() as session:
                tenant = resolve_worker_tenant(
                    session,
                    organization_id=message.organization_id,
                    job_id=message.job_id,
                    document_id=message.document_id,
                )
                claim = ProcessingJobRepository(session, tenant).claim(
                    job_id=message.job_id,
                    document_id=message.document_id,
                )
                if claim.state != JobClaimState.CLAIMED:
                    return claim.state

                document = DocumentRepository(session, tenant).mark_processing(
                    message.document_id
                )
                keys = build_document_keys(
                    organization_id=message.organization_id,
                    document_id=message.document_id,
                    quarantine_prefix=self.quarantine_prefix,
                    validated_prefix=self.validated_prefix,
                )
                if document.storage_key != keys.quarantine_key:
                    raise ValueError("Document storage state is invalid.")
                AuditEventRepository(session, tenant).append(
                    action="document.processing_started",
                    resource_type="document",
                    resource_id=str(message.document_id),
                    request_id=str(message.request_id),
                    safe_metadata={
                        "attempt_count": claim.job.attempt_count,
                        "job_id": str(message.job_id),
                        "queue_receive_count": received.receive_count,
                    },
                )
                return claim.state
        except TenantResourceNotFound:
            raise
        except (SQLAlchemyError, ValueError):
            raise WorkerExecutionError("The processing job could not be claimed safely.") from None

    def _load_document(self, message: ProcessingMessage):
        with self.database.transaction() as session:
            tenant = resolve_worker_tenant(
                session,
                organization_id=message.organization_id,
                job_id=message.job_id,
                document_id=message.document_id,
            )
            return DocumentRepository(session, tenant).require(message.document_id)

    def _complete(
        self,
        *,
        message: ProcessingMessage,
        received: ReceivedQueueMessage,
        processed: ProcessedDocument,
        validated_key: str,
    ) -> None:
        with self.database.transaction() as session:
            tenant = resolve_worker_tenant(
                session,
                organization_id=message.organization_id,
                job_id=message.job_id,
                document_id=message.document_id,
            )
            job = ProcessingJobRepository(session, tenant).complete(
                job_id=message.job_id,
                document_id=message.document_id,
                extraction_result=processed.result,
                evidence=processed.evidence,
            )
            DocumentRepository(session, tenant).mark_completed(
                message.document_id,
                storage_key=validated_key,
            )
            workflow_result = processed.result.get("workflow_result") or {}
            AuditEventRepository(session, tenant).append(
                action="document.processing_completed",
                resource_type="document",
                resource_id=str(message.document_id),
                request_id=str(message.request_id),
                safe_metadata={
                    "attempt_count": job.attempt_count,
                    "evidence_count": len(processed.evidence),
                    "job_id": str(message.job_id),
                    "queue_receive_count": received.receive_count,
                    "storage_state": "validated",
                    "workflow_type": workflow_result.get("workflow_type"),
                },
            )

    def _record_failure(
        self,
        *,
        message: ProcessingMessage,
        received: ReceivedQueueMessage,
        error_code: str,
        error_category: str,
        promoted: bool,
        validated_key: str,
    ) -> None:
        try:
            with self.database.transaction() as session:
                tenant = resolve_worker_tenant(
                    session,
                    organization_id=message.organization_id,
                    job_id=message.job_id,
                    document_id=message.document_id,
                )
                ProcessingJobRepository(session, tenant).mark_failed(
                    job_id=message.job_id,
                    document_id=message.document_id,
                    error_code=error_code,
                    error_category=error_category,
                )
                DocumentRepository(session, tenant).mark_failed(
                    message.document_id,
                    storage_key=validated_key if promoted else None,
                )
                AuditEventRepository(session, tenant).append(
                    action="document.processing_failed",
                    resource_type="document",
                    resource_id=str(message.document_id),
                    request_id=str(message.request_id),
                    safe_metadata={
                        "error_category": error_category,
                        "error_code": error_code,
                        "job_id": str(message.job_id),
                        "queue_receive_count": received.receive_count,
                    },
                )
        except Exception:
            raise WorkerExecutionError("The processing failure could not be recorded safely.") from None

    def _acknowledge(
        self,
        *,
        outcome: WorkerOutcome,
        received: ReceivedQueueMessage,
        job_id: uuid.UUID,
    ) -> WorkerRunResult:
        try:
            self.queue.delete(receipt_handle=received.receipt_handle)
        except QueueOperationError:
            return self._result(WorkerOutcome.ACK_FAILED, received, job_id)
        return self._result(outcome, received, job_id)

    @staticmethod
    def _result(
        outcome: WorkerOutcome,
        received: ReceivedQueueMessage,
        job_id: uuid.UUID | None = None,
    ) -> WorkerRunResult:
        return WorkerRunResult(
            outcome=outcome,
            message_id=received.message_id,
            job_id=job_id,
            receive_count=received.receive_count,
        )
