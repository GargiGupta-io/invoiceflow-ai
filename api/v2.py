from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_db_session,
    require_read_tenant,
    require_review_tenant,
    require_tenant,
    require_upload_tenant,
)
from app.config import get_settings
from app.db.repositories import (
    AuditEventRepository,
    DocumentRepository,
    ReviewDecisionRepository,
    TenantResourceNotFound,
)
from app.db.repositories.jobs import ProcessingJobRepository
from app.db.tenant import TenantContext
from app.ingest import (
    UploadPersistenceError,
    UploadValidationError,
    UploadValidator,
    persist_quarantined_upload,
)
from app.schemas.persistence import (
    AuditEventResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentSummaryResponse,
    DocumentUploadResponse,
    ProcessingJobResponse,
    ReviewCreateRequest,
    ReviewDecisionResponse,
    TenantIdentityResponse,
)
from app.storage import ObjectStorage, get_object_storage


router = APIRouter(prefix="/v2", tags=["Version 2 persistence"])


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "resource_not_found", "message": "Resource was not found."},
    )


@lru_cache
def get_upload_validator() -> UploadValidator:
    return UploadValidator.from_settings(get_settings())


def _upload_validation_error(error: UploadValidationError) -> HTTPException:
    if error.code == "file_too_large":
        status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    elif error.code in {
        "content_type_not_allowed",
        "extension_not_allowed",
        "file_signature_invalid",
        "file_type_mismatch",
    }:
        status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    elif error.code in {
        "encrypted_pdf",
        "file_unreadable",
        "pdf_page_limit_exceeded",
    }:
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    else:
        status_code = status.HTTP_400_BAD_REQUEST
    return HTTPException(
        status_code=status_code,
        detail={"code": error.code, "message": str(error)},
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


@router.post(
    "/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: Annotated[UploadFile, File(description="PDF, PNG, or JPEG finance document")],
    tenant: TenantContext = Depends(require_upload_tenant),
    session: Session = Depends(get_db_session),
    storage: ObjectStorage = Depends(get_object_storage),
    validator: UploadValidator = Depends(get_upload_validator),
) -> DocumentUploadResponse:
    try:
        content = await file.read(validator.max_bytes + 1)
        upload = validator.validate(
            filename=file.filename or "",
            declared_content_type=file.content_type or "",
            content=content,
        )
    except UploadValidationError as error:
        raise _upload_validation_error(error) from error
    finally:
        await file.close()

    settings = get_settings()
    try:
        receipt = persist_quarantined_upload(
            session=session,
            tenant=tenant,
            storage=storage,
            upload=upload,
            quarantine_prefix=settings.s3_quarantine_prefix,
            validated_prefix=settings.s3_validated_prefix,
        )
    except UploadPersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": error.code, "message": str(error)},
        ) from error

    return DocumentUploadResponse(
        document=DocumentSummaryResponse.model_validate(receipt.document),
        request_id=receipt.request_id,
    )


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
