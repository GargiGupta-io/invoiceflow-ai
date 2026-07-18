from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import DocumentStatus, ProcessingJob
from app.db.repositories import (
    AuditEventRepository,
    DocumentRepository,
    ProcessingJobRepository,
)
from app.db.tenant import TenantContext
from app.queue import ProcessingMessage, ProcessingQueue, QueueOperationError
from app.storage import build_document_keys


class ProcessingDispatchError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class DocumentProcessingStateError(ValueError):
    """The document cannot enter processing from its current storage state."""


@dataclass(frozen=True)
class ProcessingDispatchReceipt:
    job: ProcessingJob
    request_id: uuid.UUID
    reused_job: bool


def dispatch_processing_job(
    *,
    session: Session,
    tenant: TenantContext,
    queue: ProcessingQueue,
    document_id: uuid.UUID,
    idempotency_key: str,
    quarantine_prefix: str,
    validated_prefix: str,
) -> ProcessingDispatchReceipt:
    request_id = uuid.uuid4()
    document = DocumentRepository(session, tenant).require(document_id)
    jobs = ProcessingJobRepository(session, tenant)
    existing = jobs.get_by_idempotency_key(idempotency_key)

    if existing is None:
        expected_key = build_document_keys(
            organization_id=tenant.organization_id,
            document_id=document.id,
            quarantine_prefix=quarantine_prefix,
            validated_prefix=validated_prefix,
        ).quarantine_key
        if document.status is not DocumentStatus.QUARANTINED or document.storage_key != expected_key:
            raise DocumentProcessingStateError(
                "The document is not ready to enter processing."
            )

    try:
        reservation = jobs.reserve(
            document_id=document.id,
            idempotency_key=idempotency_key,
        )
        if not reservation.reused:
            document.status = DocumentStatus.QUEUED
            AuditEventRepository(session, tenant).append(
                action="document.processing_requested",
                resource_type="document",
                resource_id=str(document.id),
                request_id=str(request_id),
                safe_metadata={
                    "job_id": str(reservation.job.id),
                    "processing_state": "queued",
                },
            )
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise ProcessingDispatchError(
            "processing_job_unavailable",
            "The processing request could not be saved. Try again later.",
        ) from None

    message = ProcessingMessage(
        job_id=reservation.job.id,
        document_id=document.id,
        organization_id=tenant.organization_id,
        request_id=request_id,
    )
    try:
        dispatch = queue.send(message)
    except QueueOperationError:
        raise ProcessingDispatchError(
            "processing_queue_unavailable",
            "The processing request was saved but could not be queued. Retry with the same idempotency key.",
        ) from None

    try:
        AuditEventRepository(session, tenant).append(
            action="document.processing_dispatched",
            resource_type="document",
            resource_id=str(document.id),
            request_id=str(request_id),
            safe_metadata={
                "delivery_model": "at_least_once",
                "job_id": str(reservation.job.id),
                "queue_message_id": dispatch.message_id,
                "reused_job": reservation.reused,
                "schema_version": message.schema_version,
            },
        )
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise ProcessingDispatchError(
            "dispatch_audit_unavailable",
            "The processing request was queued but could not be recorded safely.",
        ) from None

    return ProcessingDispatchReceipt(
        job=reservation.job,
        request_id=request_id,
        reused_job=reservation.reused,
    )
