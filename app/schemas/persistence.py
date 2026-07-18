from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import DocumentStatus, JobStatus, ReviewAction


class TenantIdentityResponse(BaseModel):
    organization_id: uuid.UUID
    actor_id: uuid.UUID


class DocumentSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    content_type: str
    size_bytes: int
    page_count: int | None
    status: DocumentStatus
    retention_until: datetime | None
    created_at: datetime
    updated_at: datetime


class ProcessingJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    status: JobStatus
    attempt_count: int
    max_attempts: int
    error_code: str | None
    error_category: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ReviewDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    processing_job_id: uuid.UUID
    actor_user_id: uuid.UUID
    action: ReviewAction
    reason: str
    reviewer_note: str | None
    created_at: datetime


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: str
    timestamp: datetime
    request_id: str
    safe_metadata: dict[str, Any]


class DocumentListResponse(BaseModel):
    items: list[DocumentSummaryResponse]
    count: int


class DocumentDetailResponse(BaseModel):
    document: DocumentSummaryResponse
    processing_jobs: list[ProcessingJobResponse]
    reviews: list[ReviewDecisionResponse]


class DocumentUploadResponse(BaseModel):
    document: DocumentSummaryResponse
    request_id: uuid.UUID


class DocumentAccessResponse(BaseModel):
    document_id: uuid.UUID
    request_id: uuid.UUID
    url: str = Field(min_length=1, max_length=8192)
    expires_in_seconds: int = Field(ge=60, le=300)
    expires_at: datetime


class ReviewCreateRequest(BaseModel):
    processing_job_id: uuid.UUID
    action: ReviewAction
    reason: str = Field(min_length=1, max_length=500)
    reviewer_note: str | None = Field(default=None, max_length=5000)
