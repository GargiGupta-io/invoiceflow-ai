from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_db_session,
    require_read_tenant,
    require_review_tenant,
    require_tenant,
)
from app.db.repositories import (
    AuditEventRepository,
    DocumentRepository,
    ReviewDecisionRepository,
    TenantResourceNotFound,
)
from app.db.repositories.jobs import ProcessingJobRepository
from app.db.tenant import TenantContext
from app.schemas.persistence import (
    AuditEventResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentSummaryResponse,
    ProcessingJobResponse,
    ReviewCreateRequest,
    ReviewDecisionResponse,
    TenantIdentityResponse,
)


router = APIRouter(prefix="/v2", tags=["Version 2 persistence"])


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "resource_not_found", "message": "Resource was not found."},
    )


@router.get("/me", response_model=TenantIdentityResponse)
def current_identity(tenant: TenantContext = Depends(require_tenant)) -> TenantIdentityResponse:
    return TenantIdentityResponse(
        organization_id=tenant.organization_id,
        actor_id=tenant.actor_id,
    )


@router.get("/documents", response_model=DocumentListResponse)
def document_history(
    limit: int = Query(default=50, ge=1, le=100),
    tenant: TenantContext = Depends(require_read_tenant),
    session: Session = Depends(get_db_session),
) -> DocumentListResponse:
    documents = DocumentRepository(session, tenant).list_recent(limit=limit)
    items = [DocumentSummaryResponse.model_validate(document) for document in documents]
    return DocumentListResponse(items=items, count=len(items))


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
def document_detail(
    document_id: uuid.UUID,
    tenant: TenantContext = Depends(require_read_tenant),
    session: Session = Depends(get_db_session),
) -> DocumentDetailResponse:
    try:
        document = DocumentRepository(session, tenant).require(document_id)
        jobs = ProcessingJobRepository(session, tenant).list_for_document(document_id)
        reviews = ReviewDecisionRepository(session, tenant).list_for_document(document_id)
    except TenantResourceNotFound as error:
        raise _not_found() from error

    return DocumentDetailResponse(
        document=DocumentSummaryResponse.model_validate(document),
        processing_jobs=[ProcessingJobResponse.model_validate(job) for job in jobs],
        reviews=[ReviewDecisionResponse.model_validate(review) for review in reviews],
    )


@router.get(
    "/documents/{document_id}/reviews",
    response_model=list[ReviewDecisionResponse],
)
def review_history(
    document_id: uuid.UUID,
    tenant: TenantContext = Depends(require_read_tenant),
    session: Session = Depends(get_db_session),
) -> list[ReviewDecisionResponse]:
    try:
        reviews = ReviewDecisionRepository(session, tenant).list_for_document(document_id)
    except TenantResourceNotFound as error:
        raise _not_found() from error
    return [ReviewDecisionResponse.model_validate(review) for review in reviews]


@router.post(
    "/documents/{document_id}/reviews",
    response_model=ReviewDecisionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_review(
    document_id: uuid.UUID,
    request: ReviewCreateRequest,
    tenant: TenantContext = Depends(require_review_tenant),
    session: Session = Depends(get_db_session),
) -> ReviewDecisionResponse:
    try:
        review = ReviewDecisionRepository(session, tenant).create(
            document_id=document_id,
            processing_job_id=request.processing_job_id,
            action=request.action,
            reason=request.reason,
            reviewer_note=request.reviewer_note,
            decision_payload={"source": "reviewer_api"},
        )
    except TenantResourceNotFound as error:
        raise _not_found() from error

    AuditEventRepository(session, tenant).append(
        action=f"review.{request.action.value}",
        resource_type="document",
        resource_id=str(document_id),
        request_id=str(uuid.uuid4()),
        safe_metadata={
            "processing_job_id": str(request.processing_job_id),
            "review_id": str(review.id),
        },
    )
    return ReviewDecisionResponse.model_validate(review)


@router.get(
    "/documents/{document_id}/audit",
    response_model=list[AuditEventResponse],
)
def audit_history(
    document_id: uuid.UUID,
    tenant: TenantContext = Depends(require_read_tenant),
    session: Session = Depends(get_db_session),
) -> list[AuditEventResponse]:
    try:
        DocumentRepository(session, tenant).require(document_id)
    except TenantResourceNotFound as error:
        raise _not_found() from error

    events = AuditEventRepository(session, tenant).list_for_resource(
        "document",
        str(document_id),
    )
    return [AuditEventResponse.model_validate(event) for event in events]
