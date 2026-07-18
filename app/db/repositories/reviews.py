from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import ProcessingJob, ReviewAction, ReviewDecision
from app.db.repositories.base import TenantRepository, TenantResourceNotFound
from app.db.repositories.documents import DocumentRepository
from app.db.tenant import TenantContext


class ReviewDecisionRepository(TenantRepository):
    def __init__(self, session: Session, tenant: TenantContext) -> None:
        super().__init__(session, tenant)

    def create(
        self,
        *,
        document_id: uuid.UUID,
        processing_job_id: uuid.UUID,
        action: ReviewAction,
        reason: str,
        reviewer_note: str | None = None,
        decision_payload: dict[str, Any] | None = None,
    ) -> ReviewDecision:
        DocumentRepository(self.session, self.tenant).require(document_id)
        job = self._require_owned(ProcessingJob, processing_job_id)
        if job.document_id != document_id:
            raise TenantResourceNotFound("Resource was not found.")

        review = ReviewDecision(
            organization_id=self.tenant.organization_id,
            document_id=document_id,
            processing_job_id=processing_job_id,
            actor_user_id=self.tenant.actor_id,
            action=action,
            reason=reason,
            reviewer_note=reviewer_note,
            decision_payload=decision_payload or {},
        )
        self.session.add(review)
        self.session.flush()
        return review

    def list_for_document(self, document_id: uuid.UUID) -> list[ReviewDecision]:
        DocumentRepository(self.session, self.tenant).require(document_id)
        statement = (
            select(ReviewDecision)
            .where(
                ReviewDecision.organization_id == self.tenant.organization_id,
                ReviewDecision.document_id == document_id,
            )
            .order_by(ReviewDecision.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def purge_for_document(self, document_id: uuid.UUID) -> int:
        result = self.session.execute(
            delete(ReviewDecision).where(
                ReviewDecision.organization_id == self.tenant.organization_id,
                ReviewDecision.document_id == document_id,
            )
        )
        self.session.flush()
        return result.rowcount or 0
