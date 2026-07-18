"""create tenant-aware document workflow schema

Revision ID: 20260718_0001
Revises:
Create Date: 2026-07-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260718_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


document_status = sa.Enum(
    "quarantined",
    "validated",
    "queued",
    "processing",
    "completed",
    "failed",
    "deleted",
    name="document_status",
    native_enum=False,
    create_constraint=True,
)
job_status = sa.Enum(
    "queued",
    "processing",
    "completed",
    "failed",
    "dead_lettered",
    name="job_status",
    native_enum=False,
    create_constraint=True,
)
review_action = sa.Enum(
    "approved",
    "rejected",
    "returned_for_info",
    "escalated",
    name="review_action",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
    )
    op.create_table(
        "users",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("external_subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_users_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("id", "organization_id", name="uq_users_id_organization"),
        sa.UniqueConstraint(
            "organization_id",
            "external_subject",
            name="uq_users_organization_external_subject",
        ),
    )
    op.create_index("ix_users_organization_email", "users", ["organization_id", "email"])

    op.create_table(
        "documents",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("status", document_status, server_default=sa.text("'quarantined'"), nullable=False),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("page_count IS NULL OR page_count > 0", name=op.f("ck_documents_positive_page_count")),
        sa.CheckConstraint("size_bytes > 0", name=op.f("ck_documents_positive_size")),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_documents_uploader_tenant",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
        sa.UniqueConstraint("id", "organization_id", name="uq_documents_id_organization"),
        sa.UniqueConstraint("storage_key", name="uq_documents_storage_key"),
    )
    op.create_index("ix_documents_organization_created", "documents", ["organization_id", "created_at"])
    op.create_index("ix_documents_organization_status", "documents", ["organization_id", "status"])

    op.create_table(
        "processing_jobs",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("status", job_status, server_default=sa.text("'queued'"), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default=sa.text("4"), nullable=False),
        sa.Column("extraction_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_category", sa.String(length=100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("attempt_count >= 0", name=op.f("ck_processing_jobs_nonnegative_attempt_count")),
        sa.CheckConstraint("max_attempts > 0", name=op.f("ck_processing_jobs_positive_max_attempts")),
        sa.ForeignKeyConstraint(
            ["document_id", "organization_id"],
            ["documents.id", "documents.organization_id"],
            name="fk_processing_jobs_document_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_processing_jobs_requester_tenant",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_processing_jobs")),
        sa.UniqueConstraint("id", "organization_id", name="uq_processing_jobs_id_organization"),
        sa.UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_processing_jobs_organization_idempotency",
        ),
    )
    op.create_index("ix_processing_jobs_document_created", "processing_jobs", ["document_id", "created_at"])
    op.create_index("ix_processing_jobs_organization_status", "processing_jobs", ["organization_id", "status"])

    op.create_table(
        "review_decisions",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("processing_job_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("action", review_action, nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("decision_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_user_id", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_review_decisions_actor_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["document_id", "organization_id"],
            ["documents.id", "documents.organization_id"],
            name="fk_review_decisions_document_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["processing_job_id", "organization_id"],
            ["processing_jobs.id", "processing_jobs.organization_id"],
            name="fk_review_decisions_job_tenant",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review_decisions")),
    )
    op.create_index("ix_review_decisions_document_created", "review_decisions", ["document_id", "created_at"])
    op.create_index(
        "ix_review_decisions_organization_created",
        "review_decisions",
        ["organization_id", "created_at"],
    )

    op.create_table(
        "audit_events",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=100), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("request_id", sa.String(length=100), nullable=False),
        sa.Column("safe_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_id", "organization_id"],
            ["users.id", "users.organization_id"],
            name="fk_audit_events_actor_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_audit_events_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index("ix_audit_events_request_id", "audit_events", ["request_id"])
    op.create_index(
        "ix_audit_events_organization_resource",
        "audit_events",
        ["organization_id", "resource_type", "resource_id"],
    )
    op.create_index(
        "ix_audit_events_organization_timestamp",
        "audit_events",
        ["organization_id", "timestamp"],
    )

    op.execute(
        """
        CREATE FUNCTION prevent_audit_event_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_events_append_only
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_event_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_events_append_only ON audit_events")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_event_mutation()")
    op.drop_index("ix_audit_events_organization_timestamp", table_name="audit_events")
    op.drop_index("ix_audit_events_organization_resource", table_name="audit_events")
    op.drop_index("ix_audit_events_request_id", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_review_decisions_organization_created", table_name="review_decisions")
    op.drop_index("ix_review_decisions_document_created", table_name="review_decisions")
    op.drop_table("review_decisions")
    op.drop_index("ix_processing_jobs_organization_status", table_name="processing_jobs")
    op.drop_index("ix_processing_jobs_document_created", table_name="processing_jobs")
    op.drop_table("processing_jobs")
    op.drop_index("ix_documents_organization_status", table_name="documents")
    op.drop_index("ix_documents_organization_created", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_users_organization_email", table_name="users")
    op.drop_table("users")
    op.drop_table("organizations")
