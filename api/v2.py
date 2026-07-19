from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_db_session,
    require_delete_tenant,
    require_process_tenant,
    require_read_tenant,
    require_review_tenant,
    require_tenant,
    require_upload_tenant,
)
from app.config import Settings, get_settings
from app.db.repositories import (
    AuditEventRepository,
    DocumentPageRepository,
    DocumentRepository,
    ReviewDecisionRepository,
    TenantResourceNotFound,
    IdempotencyConflict,
)
from app.db.repositories.jobs import ProcessingJobRepository
from app.db.tenant import TenantContext
from app.ingest import (
    UploadPersistenceError,
    UploadValidationError,
    UploadValidator,
    persist_quarantined_upload,
)
from app.processing import (
    DocumentProcessingStateError,
    ProcessingDispatchError,
    dispatch_processing_job,
)
from app.queue import ProcessingQueue, get_processing_queue
from app.schemas.persistence import (
    AuditEventResponse,
    DocumentAccessResponse,
    DocumentDetailResponse,
    DocumentDeletionResponse,
    DocumentListResponse,
    DocumentPageListResponse,
    DocumentPageResponse,
    DocumentSearchHitResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentSummaryResponse,
    DocumentUploadResponse,
    ProcessingJobResponse,
    ProcessingDispatchResponse,
    ReviewCreateRequest,
    ReviewDecisionResponse,
    ReviewerAuthConfigResponse,
    TenantIdentityResponse,
)
from app.storage import (
    ObjectStorage,
    StorageOperationError,
    build_document_keys,
    get_object_storage,
)
from app.retention import (
    DeletionReason,
    DocumentDeletionConflict,
    DocumentDeletionService,
)


router = APIRouter(prefix="/v2", tags=["Version 2 persistence"])

REVIEWER_SCOPES = [
    "openid",
    "email",
    "invoiceflow/read",
    "invoiceflow/upload",
    "invoiceflow/process",
    "invoiceflow/review",
    "invoiceflow/delete",
]


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "resource_not_found", "message": "Resource was not found."},
    )


def _document_not_ready() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "document_not_ready",
            "message": "The document is not ready for private access.",
        },
    )


@lru_cache
def get_upload_validator() -> UploadValidator:
    return UploadValidator.from_settings(get_settings())


@router.get("/auth/config", response_model=ReviewerAuthConfigResponse)
def reviewer_auth_config(
    response: Response,
    settings: Settings = Depends(get_settings),
) -> ReviewerAuthConfigResponse:
    response.headers["Cache-Control"] = "no-store"
    if not settings.auth_browser_configured:
        return ReviewerAuthConfigResponse(configured=False)

    browser_domain = settings.auth_browser_domain.rstrip("/")
    issuer = settings.auth_issuer.rstrip("/")
    return ReviewerAuthConfigResponse(
        configured=True,
        issuer=issuer,
        client_id=settings.auth_client_id,
        authorization_endpoint=f"{browser_domain}/oauth2/authorize",
        token_endpoint=f"{browser_domain}/oauth2/token",
        logout_endpoint=f"{browser_domain}/logout",
        jwks_uri=f"{issuer}/.well-known/jwks.json",
        redirect_uri=settings.auth_redirect_uri,
        post_logout_redirect_uri=settings.auth_logout_uri,
        scopes=REVIEWER_SCOPES,
    )


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
            retention_days=settings.document_retention_days,
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
    "/documents/{document_id}/pages",
    response_model=DocumentPageListResponse,
)
def document_pages(
    document_id: uuid.UUID,
    response: Response,
    tenant: TenantContext = Depends(require_read_tenant),
    session: Session = Depends(get_db_session),
) -> DocumentPageListResponse:
    try:
        pages = DocumentPageRepository(session, tenant).list_for_document(document_id)
    except TenantResourceNotFound as error:
        raise _not_found() from error

    response.headers["Cache-Control"] = "no-store"
    items = [
        DocumentPageResponse(
            page_number=page.page_number,
            text=page.text_content,
            extraction_method=page.extraction_method,
            warnings=list(page.warnings),
        )
        for page in pages
    ]
    return DocumentPageListResponse(
        document_id=document_id,
        items=items,
        count=len(items),
    )


@router.post("/search", response_model=DocumentSearchResponse)
def search_documents(
    request: DocumentSearchRequest,
    response: Response,
    tenant: TenantContext = Depends(require_read_tenant),
    session: Session = Depends(get_db_session),
) -> DocumentSearchResponse:
    hits = DocumentPageRepository(session, tenant).search(
        request.query,
        limit=request.limit,
    )
    response.headers["Cache-Control"] = "no-store"
    items = [
        DocumentSearchHitResponse(
            document_id=hit.document_id,
            page_number=hit.page_number,
            excerpt=hit.excerpt,
            extraction_method=hit.extraction_method,
            score=hit.score,
            access_path=f"/v2/documents/{hit.document_id}/access",
            page_fragment=f"#page={hit.page_number}",
        )
        for hit in hits
    ]
    return DocumentSearchResponse(items=items, count=len(items))


@router.delete(
    "/documents/{document_id}",
    response_model=DocumentDeletionResponse,
)
def delete_document(
    document_id: uuid.UUID,
    tenant: TenantContext = Depends(require_delete_tenant),
    session: Session = Depends(get_db_session),
    storage: ObjectStorage = Depends(get_object_storage),
) -> DocumentDeletionResponse:
    settings = get_settings()
    service = DocumentDeletionService(
        storage=storage,
        quarantine_prefix=settings.s3_quarantine_prefix,
        validated_prefix=settings.s3_validated_prefix,
    )
    try:
        result = service.delete(
            session=session,
            tenant=tenant,
            document_id=document_id,
            reason=DeletionReason.USER_REQUESTED,
        )
    except TenantResourceNotFound as error:
        raise _not_found() from error
    except DocumentDeletionConflict as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "document_processing_active",
                "message": str(error),
            },
        ) from error
    except StorageOperationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "storage_unavailable",
                "message": "The document could not be deleted safely. Try again later.",
            },
        ) from None

    return DocumentDeletionResponse(
        document_id=result.document_id,
        deleted_at=result.deleted_at,
        already_deleted=result.already_deleted,
        request_id=result.request_id,
    )


@router.post(
    "/documents/{document_id}/access",
    response_model=DocumentAccessResponse,
)
def create_document_access(
    document_id: uuid.UUID,
    response: Response,
    tenant: TenantContext = Depends(require_read_tenant),
    session: Session = Depends(get_db_session),
    storage: ObjectStorage = Depends(get_object_storage),
) -> DocumentAccessResponse:
    settings = get_settings()
    try:
        document = DocumentRepository(session, tenant).require(document_id)
    except TenantResourceNotFound as error:
        raise _not_found() from error

    expected_key = build_document_keys(
        organization_id=tenant.organization_id,
        document_id=document.id,
        quarantine_prefix=settings.s3_quarantine_prefix,
        validated_prefix=settings.s3_validated_prefix,
    ).validated_key
    if document.storage_key != expected_key:
        raise _document_not_ready()

    request_id = uuid.uuid4()
    issued_at = datetime.now(timezone.utc)
    try:
        url = storage.create_download_url(
            key=expected_key,
            expires_in_seconds=settings.s3_presigned_url_ttl_seconds,
        )
        AuditEventRepository(session, tenant).append(
            action="document.access_url_issued",
            resource_type="document",
            resource_id=str(document.id),
            request_id=str(request_id),
            safe_metadata={
                "content_type": document.content_type,
                "expires_in_seconds": settings.s3_presigned_url_ttl_seconds,
                "storage_state": "validated",
            },
        )
        session.commit()
    except StorageOperationError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "storage_unavailable",
                "message": "Private document access is temporarily unavailable.",
            },
        ) from None
    except SQLAlchemyError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "access_audit_unavailable",
                "message": "Private document access could not be recorded safely.",
            },
        ) from None

    response.headers["Cache-Control"] = "no-store"
    return DocumentAccessResponse(
        document_id=document.id,
        request_id=request_id,
        url=url,
        expires_in_seconds=settings.s3_presigned_url_ttl_seconds,
        expires_at=issued_at + timedelta(seconds=settings.s3_presigned_url_ttl_seconds),
    )


@router.post(
    "/documents/{document_id}/processing-jobs",
    response_model=ProcessingDispatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_processing_job(
    document_id: uuid.UUID,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=128,
            pattern=r"^[A-Za-z0-9._:-]+$",
        ),
    ],
    tenant: TenantContext = Depends(require_process_tenant),
    session: Session = Depends(get_db_session),
    queue: ProcessingQueue = Depends(get_processing_queue),
) -> ProcessingDispatchResponse:
    settings = get_settings()
    try:
        receipt = dispatch_processing_job(
            session=session,
            tenant=tenant,
            queue=queue,
            document_id=document_id,
            idempotency_key=idempotency_key,
            quarantine_prefix=settings.s3_quarantine_prefix,
            validated_prefix=settings.s3_validated_prefix,
        )
    except TenantResourceNotFound as error:
        raise _not_found() from error
    except IdempotencyConflict as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "idempotency_conflict",
                "message": "The idempotency key belongs to another processing request.",
            },
        ) from error
    except DocumentProcessingStateError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "document_not_ready", "message": str(error)},
        ) from error
    except ProcessingDispatchError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": error.code, "message": str(error)},
        ) from error

    return ProcessingDispatchResponse(
        processing_job=ProcessingJobResponse.model_validate(receipt.job),
        request_id=receipt.request_id,
        reused_job=receipt.reused_job,
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
        DocumentRepository(session, tenant).require_including_deleted(document_id)
    except TenantResourceNotFound as error:
        raise _not_found() from error

    events = AuditEventRepository(session, tenant).list_for_resource(
        "document",
        str(document_id),
    )
    return [AuditEventResponse.model_validate(event) for event in events]
