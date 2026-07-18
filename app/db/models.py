from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin, UpdatedAtMixin


class DocumentStatus(str, enum.Enum):
    QUARANTINED = "quarantined"
    VALIDATED = "validated"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETED = "deleted"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTERED = "dead_lettered"


class ReviewAction(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    RETURNED_FOR_INFO = "returned_for_info"
    ESCALATED = "escalated"


def enum_type(enum_class: type[enum.Enum], name: str) -> Enum:
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )


def json_document() -> JSON:
    return JSON().with_variant(JSONB(), "postgresql")


class Organization(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)


class User(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("id", "organization_id", name="uq_users_id_organization"),
        UniqueConstraint(
            "organization_id",
            "external_subject",
            name="uq_users_organization_external_subject",
        ),
        Index("ix_users_organization_email", "organization_id", "email"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    external_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )


class Document(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        ForeignKeyConstraint(
            ["uploaded_by_user_id", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_documents_uploader_tenant",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "organization_id", name="uq_documents_id_organization"),
        UniqueConstraint("storage_key", name="uq_documents_storage_key"),
        CheckConstraint("size_bytes > 0", name="positive_size"),
        CheckConstraint("page_count IS NULL OR page_count > 0", name="positive_page_count"),
        Index("ix_documents_organization_created", "organization_id", "created_at"),
        Index("ix_documents_organization_status", "organization_id", "status"),
        Index("ix_documents_retention_deleted", "retention_until", "deleted_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[DocumentStatus] = mapped_column(
        enum_type(DocumentStatus, "document_status"),
        default=DocumentStatus.QUARANTINED,
        server_default=text("'quarantined'"),
        nullable=False,
    )
    retention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProcessingJob(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = "processing_jobs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "organization_id"],
            ["documents.id", "documents.organization_id"],
            name="fk_processing_jobs_document_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["requested_by_user_id", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_processing_jobs_requester_tenant",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "organization_id", name="uq_processing_jobs_id_organization"),
        UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_processing_jobs_organization_idempotency",
        ),
        CheckConstraint("attempt_count >= 0", name="nonnegative_attempt_count"),
        CheckConstraint("max_attempts > 0", name="positive_max_attempts"),
        Index("ix_processing_jobs_organization_status", "organization_id", "status"),
        Index("ix_processing_jobs_document_created", "document_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        enum_type(JobStatus, "job_status"),
        default=JobStatus.QUEUED,
        server_default=text("'queued'"),
        nullable=False,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=4, server_default=text("4"), nullable=False)
    extraction_result: Mapped[dict[str, Any] | None] = mapped_column(json_document())
    evidence: Mapped[list[dict[str, Any]] | None] = mapped_column(json_document())
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_category: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReviewDecision(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "review_decisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "organization_id"],
            ["documents.id", "documents.organization_id"],
            name="fk_review_decisions_document_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["processing_job_id", "organization_id"],
            ["processing_jobs.id", "processing_jobs.organization_id"],
            name="fk_review_decisions_job_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["actor_user_id", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_review_decisions_actor_tenant",
            ondelete="RESTRICT",
        ),
        Index("ix_review_decisions_organization_created", "organization_id", "created_at"),
        Index("ix_review_decisions_document_created", "document_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    processing_job_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    action: Mapped[ReviewAction] = mapped_column(
        enum_type(ReviewAction, "review_action"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    reviewer_note: Mapped[str | None] = mapped_column(Text)
    decision_payload: Mapped[dict[str, Any]] = mapped_column(
        json_document(),
        default=dict,
        nullable=False,
    )


class AuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["actor_id", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_audit_events_actor_tenant",
            ondelete="RESTRICT",
        ),
        Index("ix_audit_events_organization_timestamp", "organization_id", "timestamp"),
        Index(
            "ix_audit_events_organization_resource",
            "organization_id",
            "resource_type",
            "resource_id",
        ),
        Index("ix_audit_events_request_id", "request_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    request_id: Mapped[str] = mapped_column(String(100), nullable=False)
    safe_metadata: Mapped[dict[str, Any]] = mapped_column(
        json_document(),
        default=dict,
        nullable=False,
    )
