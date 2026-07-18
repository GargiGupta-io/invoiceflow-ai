from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import JobStatus, ProcessingJob
from app.db.repositories.base import IdempotencyConflict, TenantRepository
from app.db.repositories.documents import DocumentRepository
from app.db.tenant import TenantContext


@dataclass(frozen=True)
class JobReservation:
    job: ProcessingJob
    reused: bool


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
