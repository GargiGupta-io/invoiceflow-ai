from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import JobStatus, ProcessingJob
from app.db.repositories.base import (
    IdempotencyConflict,
    TenantRepository,
    TenantResourceNotFound,
)
from app.db.repositories.documents import DocumentRepository
from app.db.tenant import TenantContext


@dataclass(frozen=True)
class JobReservation:
    job: ProcessingJob
    reused: bool


class JobClaimState(str, Enum):
    CLAIMED = "claimed"
    COMPLETED = "completed"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class JobClaim:
    job: ProcessingJob
    state: JobClaimState


class JobStateConflict(RuntimeError):
    """A worker attempted a state transition that is no longer valid."""


def resolve_worker_tenant(
    session: Session,
    *,
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
    document_id: uuid.UUID,
) -> TenantContext:
    statement = select(ProcessingJob.requested_by_user_id).where(
        ProcessingJob.organization_id == organization_id,
        ProcessingJob.id == job_id,
        ProcessingJob.document_id == document_id,
    )
    actor_id = session.scalar(statement)
    if actor_id is None:
        raise TenantResourceNotFound("Resource was not found.")
    return TenantContext(organization_id=organization_id, actor_id=actor_id)


class ProcessingJobRepository(TenantRepository):
    def __init__(self, session: Session, tenant: TenantContext) -> None:
        super().__init__(session, tenant)

    def get(self, job_id: uuid.UUID) -> ProcessingJob | None:
        return self._get_owned(ProcessingJob, job_id)

    def get_by_idempotency_key(self, idempotency_key: str) -> ProcessingJob | None:
        statement = select(ProcessingJob).where(
            ProcessingJob.organization_id == self.tenant.organization_id,
            ProcessingJob.idempotency_key == idempotency_key,
        )
        return self.session.scalar(statement)

    def get_or_create(
        self,
        *,
        document_id: uuid.UUID,
        idempotency_key: str,
        max_attempts: int = 4,
    ) -> ProcessingJob:
        return self.reserve(
            document_id=document_id,
            idempotency_key=idempotency_key,
            max_attempts=max_attempts,
        ).job

    def reserve(
        self,
        *,
        document_id: uuid.UUID,
        idempotency_key: str,
        max_attempts: int = 4,
    ) -> JobReservation:
        DocumentRepository(self.session, self.tenant).require(document_id)
        existing = self.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            if existing.document_id != document_id:
                raise IdempotencyConflict(
                    "Idempotency key is already associated with another document."
                )
            return JobReservation(job=existing, reused=True)

        job = ProcessingJob(
            organization_id=self.tenant.organization_id,
            document_id=document_id,
            requested_by_user_id=self.tenant.actor_id,
            idempotency_key=idempotency_key,
            status=JobStatus.QUEUED,
            max_attempts=max_attempts,
        )
        try:
            with self.session.begin_nested():
                self.session.add(job)
                self.session.flush()
        except IntegrityError:
            existing = self.get_by_idempotency_key(idempotency_key)
            if existing is None:
                raise
            if existing.document_id != document_id:
                raise IdempotencyConflict(
                    "Idempotency key is already associated with another document."
                ) from None
            return JobReservation(job=existing, reused=True)
        return JobReservation(job=job, reused=False)

    def list_for_document(self, document_id: uuid.UUID) -> list[ProcessingJob]:
        DocumentRepository(self.session, self.tenant).require(document_id)
        statement = (
            select(ProcessingJob)
            .where(
                ProcessingJob.organization_id == self.tenant.organization_id,
                ProcessingJob.document_id == document_id,
            )
            .order_by(ProcessingJob.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def claim(self, *, job_id: uuid.UUID, document_id: uuid.UUID) -> JobClaim:
        now = datetime.now(timezone.utc)
        statement = (
            update(ProcessingJob)
            .where(
                ProcessingJob.organization_id == self.tenant.organization_id,
                ProcessingJob.id == job_id,
                ProcessingJob.document_id == document_id,
                ProcessingJob.status == JobStatus.QUEUED,
            )
            .values(
                status=JobStatus.PROCESSING,
                attempt_count=ProcessingJob.attempt_count + 1,
                started_at=now,
                completed_at=None,
                error_code=None,
                error_category=None,
            )
            .returning(ProcessingJob)
        )
        claimed = self.session.scalar(statement)
        if claimed is not None:
            return JobClaim(job=claimed, state=JobClaimState.CLAIMED)

        existing = self.get(job_id)
        if existing is None or existing.document_id != document_id:
            raise TenantResourceNotFound("Resource was not found.")
        state = (
            JobClaimState.COMPLETED
            if existing.status == JobStatus.COMPLETED
            else JobClaimState.UNAVAILABLE
        )
        return JobClaim(job=existing, state=state)

    def complete(
        self,
        *,
        job_id: uuid.UUID,
        document_id: uuid.UUID,
        extraction_result: dict[str, Any],
        evidence: list[dict[str, Any]],
    ) -> ProcessingJob:
        job = self._require_job_document(job_id=job_id, document_id=document_id)
        if job.status == JobStatus.COMPLETED:
            return job
        if job.status != JobStatus.PROCESSING:
            raise JobStateConflict("Processing job is not active.")
        job.status = JobStatus.COMPLETED
        job.extraction_result = dict(extraction_result)
        job.evidence = list(evidence)
        job.error_code = None
        job.error_category = None
        job.completed_at = datetime.now(timezone.utc)
        self.session.flush()
        return job

    def mark_failed(
        self,
        *,
        job_id: uuid.UUID,
        document_id: uuid.UUID,
        error_code: str,
        error_category: str,
    ) -> ProcessingJob:
        job = self._require_job_document(job_id=job_id, document_id=document_id)
        if job.status == JobStatus.COMPLETED:
            return job
        if job.status not in {JobStatus.PROCESSING, JobStatus.QUEUED}:
            return job
        job.status = JobStatus.FAILED
        job.error_code = error_code[:100]
        job.error_category = error_category[:100]
        job.completed_at = datetime.now(timezone.utc)
        self.session.flush()
        return job

    def _require_job_document(
        self,
        *,
        job_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> ProcessingJob:
        job = self.get(job_id)
        if job is None or job.document_id != document_id:
            raise TenantResourceNotFound("Resource was not found.")
        return job
