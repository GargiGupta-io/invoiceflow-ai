from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentStatus
from app.db.repositories import (
    AuditEventRepository,
    DocumentRepository,
    ProcessingJobRepository,
    ReviewDecisionRepository,
    TenantResourceNotFound,
)
from app.db.session import Database
from app.db.tenant import TenantContext
from app.storage import ObjectStorage, StorageOperationError, build_document_keys


class DeletionReason(str, Enum):
    USER_REQUESTED = "user_requested"
    RETENTION_EXPIRED = "retention_expired"


class DocumentDeletionConflict(RuntimeError):
    """A document cannot be deleted while its processing job is active."""


@dataclass(frozen=True)
class DocumentDeletionResult:
    document_id: uuid.UUID
    deleted_at: datetime
    already_deleted: bool
    request_id: uuid.UUID
    processing_jobs_removed: int = 0
    review_decisions_removed: int = 0


@dataclass(frozen=True)
class RetentionCandidate:
    document_id: uuid.UUID
    organization_id: uuid.UUID
    uploaded_by_user_id: uuid.UUID


@dataclass(frozen=True)
class RetentionRunResult:
    candidates: int
    deleted: int
    already_deleted: int
    skipped_active: int
    failed: int


class DocumentDeletionService:
    def __init__(
        self,
        *,
        storage: ObjectStorage,
        quarantine_prefix: str,
        validated_prefix: str,
    ) -> None:
        self.storage = storage
        self.quarantine_prefix = quarantine_prefix
        self.validated_prefix = validated_prefix

    def delete(
        self,
        *,
        session: Session,
        tenant: TenantContext,
        document_id: uuid.UUID,
        reason: DeletionReason,
        system_actor: bool = False,
        now: datetime | None = None,
    ) -> DocumentDeletionResult:
        deleted_at = now or datetime.now(timezone.utc)
        request_id = uuid.uuid4()
        documents = DocumentRepository(session, tenant)
        document = documents.require_including_deleted(document_id)
        if document.deleted_at is not None:
            return DocumentDeletionResult(
                document_id=document.id,
                deleted_at=_as_utc(document.deleted_at),
                already_deleted=True,
                request_id=request_id,
            )

        jobs = ProcessingJobRepository(session, tenant)
        if jobs.has_active_for_document(document_id):
            raise DocumentDeletionConflict(
                "The document cannot be deleted while processing is active."
            )

        keys = build_document_keys(
            organization_id=tenant.organization_id,
            document_id=document_id,
            quarantine_prefix=self.quarantine_prefix,
            validated_prefix=self.validated_prefix,
        )
        self.storage.delete(key=keys.quarantine_key)
        self.storage.delete(key=keys.validated_key)

        reviews_removed = ReviewDecisionRepository(session, tenant).purge_for_document(
            document_id
        )
        jobs_removed = jobs.purge_for_document(document_id)
        documents.mark_deleted(document_id, deleted_at=deleted_at)

        audit = AuditEventRepository(session, tenant)
        append = audit.append_system if system_actor else audit.append
        append(
            action="document.deleted",
            resource_type="document",
            resource_id=str(document_id),
            request_id=str(request_id),
            safe_metadata={
                "deletion_reason": reason.value,
                "processing_jobs_removed": jobs_removed,
                "review_decisions_removed": reviews_removed,
            },
        )
        return DocumentDeletionResult(
            document_id=document_id,
            deleted_at=deleted_at,
            already_deleted=False,
            request_id=request_id,
            processing_jobs_removed=jobs_removed,
            review_decisions_removed=reviews_removed,
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def list_retention_candidates(
    session: Session,
    *,
    now: datetime,
    limit: int,
) -> list[RetentionCandidate]:
    statement = (
        select(
            Document.id,
            Document.organization_id,
            Document.uploaded_by_user_id,
        )
        .where(
            Document.retention_until.is_not(None),
            Document.retention_until <= now,
            Document.deleted_at.is_(None),
            Document.status.notin_({DocumentStatus.QUEUED, DocumentStatus.PROCESSING}),
        )
        .order_by(Document.retention_until.asc(), Document.id.asc())
        .limit(limit)
    )
    return [
        RetentionCandidate(
            document_id=row.id,
            organization_id=row.organization_id,
            uploaded_by_user_id=row.uploaded_by_user_id,
        )
        for row in session.execute(statement)
    ]


class RetentionDeletionWorker:
    def __init__(
        self,
        *,
        database: Database,
        deletion_service: DocumentDeletionService,
        batch_size: int = 100,
    ) -> None:
        if batch_size < 1:
            raise ValueError("Retention deletion batch size must be positive.")
        self.database = database
        self.deletion_service = deletion_service
        self.batch_size = batch_size

    def run_once(self, *, now: datetime | None = None) -> RetentionRunResult:
        run_at = now or datetime.now(timezone.utc)
        with self.database.transaction() as session:
            candidates = list_retention_candidates(
                session,
                now=run_at,
                limit=self.batch_size,
            )

        deleted = 0
        already_deleted = 0
        skipped_active = 0
        failed = 0
        for candidate in candidates:
            tenant = TenantContext(
                organization_id=candidate.organization_id,
                actor_id=candidate.uploaded_by_user_id,
            )
            try:
                with self.database.transaction() as session:
                    result = self.deletion_service.delete(
                        session=session,
                        tenant=tenant,
                        document_id=candidate.document_id,
                        reason=DeletionReason.RETENTION_EXPIRED,
                        system_actor=True,
                        now=run_at,
                    )
                if result.already_deleted:
                    already_deleted += 1
                else:
                    deleted += 1
            except DocumentDeletionConflict:
                skipped_active += 1
            except (SQLAlchemyError, StorageOperationError, TenantResourceNotFound):
                failed += 1

        return RetentionRunResult(
            candidates=len(candidates),
            deleted=deleted,
            already_deleted=already_deleted,
            skipped_active=skipped_active,
            failed=failed,
        )
