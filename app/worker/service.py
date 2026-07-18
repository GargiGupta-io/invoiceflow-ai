from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.exc import SQLAlchemyError

from app.db.models import JobStatus
from app.db.repositories import (
    AuditEventRepository,
    DocumentRepository,
    JobClaim,
    JobClaimState,
    JobStateConflict,
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
from app.worker.processor import (
    DocumentProcessor,
    PermanentDocumentProcessingError,
    ProcessedDocument,
)
from app.worker.visibility import VisibilityHeartbeat


class WorkerOutcome(str, Enum):
    NO_MESSAGE = "no_message"
    COMPLETED = "completed"
    ALREADY_COMPLETED = "already_completed"
    IN_PROGRESS = "in_progress"
    INVALID_MESSAGE = "invalid_message"
    UNKNOWN_JOB = "unknown_job"
    RETRY_SCHEDULED = "retry_scheduled"
    PERMANENT_FAILURE = "permanent_failure"
    RETRY_EXHAUSTED = "retry_exhausted"
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
        visibility_heartbeat_seconds: int,
        retry_base_delay_seconds: int,
        retry_max_delay_seconds: int,
        redrive_max_receive_count: int,
        stale_job_seconds: int,
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
        self.visibility_heartbeat_seconds = visibility_heartbeat_seconds
        self.retry_base_delay_seconds = retry_base_delay_seconds
        self.retry_max_delay_seconds = retry_max_delay_seconds
        self.redrive_max_receive_count = redrive_max_receive_count
        self.stale_job_seconds = stale_job_seconds

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
            self._defer_unprocessable(received)
            return self._result(WorkerOutcome.INVALID_MESSAGE, received)

        try:
            claim = self._claim(message=message, received=received)
        except TenantResourceNotFound:
            self._defer_unprocessable(received)
            return self._result(WorkerOutcome.UNKNOWN_JOB, received, message.job_id)
        if claim.state == JobClaimState.COMPLETED:
            return self._acknowledge(
                outcome=WorkerOutcome.ALREADY_COMPLETED,
                received=received,
                job_id=message.job_id,
            )
        if claim.state == JobClaimState.TERMINAL:
            self._release_to_redrive(received)
            return self._result(
                WorkerOutcome.PERMANENT_FAILURE,
                received,
                message.job_id,
            )
        if claim.state == JobClaimState.EXHAUSTED:
            if claim.job.status != JobStatus.DEAD_LETTERED:
                document = self._load_document(message)
                self._record_retry_exhausted(
                    message=message,
                    received=received,
                    error_code=claim.job.error_code or "processing_retry_limit_reached",
                    error_category=claim.job.error_category or "worker",
                    storage_key=document.storage_key,
                )
            self._release_to_redrive(received)
            return self._result(WorkerOutcome.RETRY_EXHAUSTED, received, message.job_id)
        if claim.state == JobClaimState.UNAVAILABLE:
            return self._result(WorkerOutcome.IN_PROGRESS, received, message.job_id)

        keys = build_document_keys(
            organization_id=message.organization_id,
            document_id=message.document_id,
            quarantine_prefix=self.quarantine_prefix,
            validated_prefix=self.validated_prefix,
        )
        source_key = keys.quarantine_key
        promoted = False
        try:
            document = self._load_document(message)
            source_key = document.storage_key
            promoted = source_key == keys.validated_key
            with VisibilityHeartbeat(
                queue=self.queue,
                receipt_handle=received.receipt_handle,
                visibility_timeout_seconds=self.visibility_timeout_seconds,
                interval_seconds=self.visibility_heartbeat_seconds,
            ):
                content = self.storage.read(
                    key=source_key,
                    max_bytes=self.max_document_bytes,
                )
                processed = self.processor.process(
                    filename=document.original_filename,
                    content=content,
                    content_type=document.content_type,
                )
                if not promoted:
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
        except PermanentDocumentProcessingError as error:
            self._record_permanent_failure(
                message=message,
                received=received,
                error_code=error.code,
                error_category=error.category,
                storage_key=keys.validated_key if promoted else source_key,
            )
            self._release_to_redrive(received)
            return self._result(
                WorkerOutcome.PERMANENT_FAILURE,
                received,
                message.job_id,
            )
        except StorageOperationError:
            return self._schedule_retry(
                message=message,
                received=received,
                claim=claim,
                error_code="storage_processing_failed",
                error_category="storage",
                storage_key=keys.validated_key if promoted else source_key,
            )
        except (SQLAlchemyError, TenantResourceNotFound, JobStateConflict, ValueError):
            return self._schedule_retry(
                message=message,
                received=received,
                claim=claim,
                error_code="processing_state_failed",
                error_category="persistence",
                storage_key=keys.validated_key if promoted else source_key,
            )
        except Exception:
            return self._schedule_retry(
                message=message,
                received=received,
                claim=claim,
                error_code="document_processing_failed",
                error_category="workflow",
                storage_key=keys.validated_key if promoted else source_key,
            )

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
    ) -> JobClaim:
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
                    stale_after_seconds=self.stale_job_seconds,
                )
                if claim.state != JobClaimState.CLAIMED:
                    return claim

                document = DocumentRepository(session, tenant).mark_processing(
                    message.document_id
                )
                keys = build_document_keys(
                    organization_id=message.organization_id,
                    document_id=message.document_id,
                    quarantine_prefix=self.quarantine_prefix,
                    validated_prefix=self.validated_prefix,
                )
                if document.storage_key not in {
                    keys.quarantine_key,
                    keys.validated_key,
                }:
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
                        "retry_attempt": claim.job.attempt_count > 1,
                    },
                )
                return claim
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

    def _schedule_retry(
        self,
        *,
        message: ProcessingMessage,
        received: ReceivedQueueMessage,
        claim: JobClaim,
        error_code: str,
        error_category: str,
        storage_key: str,
    ) -> WorkerRunResult:
        exhausted = (
            claim.job.attempt_count >= claim.job.max_attempts
            or received.receive_count >= self.redrive_max_receive_count
        )
        if exhausted:
            self._record_retry_exhausted(
                message=message,
                received=received,
                error_code=error_code,
                error_category=error_category,
                storage_key=storage_key,
            )
            self._release_to_redrive(received)
            return self._result(
                WorkerOutcome.RETRY_EXHAUSTED,
                received,
                message.job_id,
            )

        delay_seconds = self._retry_delay(received.receive_count)
        self._record_retry(
            message=message,
            received=received,
            error_code=error_code,
            error_category=error_category,
            storage_key=storage_key,
            delay_seconds=delay_seconds,
        )
        self._set_visibility(received, delay_seconds)
        return self._result(
            WorkerOutcome.RETRY_SCHEDULED,
            received,
            message.job_id,
        )

    def _record_retry(
        self,
        *,
        message: ProcessingMessage,
        received: ReceivedQueueMessage,
        error_code: str,
        error_category: str,
        storage_key: str,
        delay_seconds: int,
    ) -> None:
        try:
            with self.database.transaction() as session:
                tenant = resolve_worker_tenant(
                    session,
                    organization_id=message.organization_id,
                    job_id=message.job_id,
                    document_id=message.document_id,
                )
                job = ProcessingJobRepository(session, tenant).release_for_retry(
                    job_id=message.job_id,
                    document_id=message.document_id,
                    error_code=error_code,
                    error_category=error_category,
                )
                DocumentRepository(session, tenant).mark_queued_for_retry(
                    message.document_id,
                    storage_key=storage_key,
                )
                AuditEventRepository(session, tenant).append(
                    action="document.processing_retry_scheduled",
                    resource_type="document",
                    resource_id=str(message.document_id),
                    request_id=str(message.request_id),
                    safe_metadata={
                        "attempt_count": job.attempt_count,
                        "delay_seconds": delay_seconds,
                        "error_category": error_category,
                        "error_code": error_code,
                        "job_id": str(message.job_id),
                        "max_attempts": job.max_attempts,
                        "queue_receive_count": received.receive_count,
                    },
                )
        except Exception:
            raise WorkerExecutionError("The processing retry could not be recorded safely.") from None

    def _record_retry_exhausted(
        self,
        *,
        message: ProcessingMessage,
        received: ReceivedQueueMessage,
        error_code: str,
        error_category: str,
        storage_key: str,
    ) -> None:
        try:
            with self.database.transaction() as session:
                tenant = resolve_worker_tenant(
                    session,
                    organization_id=message.organization_id,
                    job_id=message.job_id,
                    document_id=message.document_id,
                )
                job = ProcessingJobRepository(session, tenant).mark_retry_exhausted(
                    job_id=message.job_id,
                    document_id=message.document_id,
                    error_code=error_code,
                    error_category=error_category,
                )
                DocumentRepository(session, tenant).mark_failed(
                    message.document_id,
                    storage_key=storage_key,
                )
                AuditEventRepository(session, tenant).append(
                    action="document.processing_retries_exhausted",
                    resource_type="document",
                    resource_id=str(message.document_id),
                    request_id=str(message.request_id),
                    safe_metadata={
                        "attempt_count": job.attempt_count,
                        "dlq_redrive_expected": True,
                        "error_category": error_category,
                        "error_code": error_code,
                        "job_id": str(message.job_id),
                        "max_attempts": job.max_attempts,
                        "queue_receive_count": received.receive_count,
                    },
                )
        except Exception:
            raise WorkerExecutionError("Retry exhaustion could not be recorded safely.") from None

    def _record_permanent_failure(
        self,
        *,
        message: ProcessingMessage,
        received: ReceivedQueueMessage,
        error_code: str,
        error_category: str,
        storage_key: str,
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
                    storage_key=storage_key,
                )
                AuditEventRepository(session, tenant).append(
                    action="document.processing_failed_permanently",
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
            raise WorkerExecutionError("The permanent failure could not be recorded safely.") from None

    def _defer_unprocessable(self, received: ReceivedQueueMessage) -> None:
        if received.receive_count >= self.redrive_max_receive_count:
            self._release_to_redrive(received)
            return
        self._set_visibility(received, self._retry_delay(received.receive_count))

    def _release_to_redrive(self, received: ReceivedQueueMessage) -> None:
        self._set_visibility(received, 0)

    def _set_visibility(
        self,
        received: ReceivedQueueMessage,
        visibility_timeout_seconds: int,
    ) -> bool:
        try:
            self.queue.change_visibility(
                receipt_handle=received.receipt_handle,
                visibility_timeout_seconds=visibility_timeout_seconds,
            )
        except QueueOperationError:
            return False
        return True

    def _retry_delay(self, receive_count: int) -> int:
        exponent = min(max(receive_count - 1, 0), 10)
        return min(
            self.retry_base_delay_seconds * (2**exponent),
            self.retry_max_delay_seconds,
        )

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
