from __future__ import annotations

import uuid
import unittest

from sqlalchemy import ForeignKeyConstraint, UniqueConstraint, create_engine, event
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError

from app.db import Base, Document, DocumentStatus, JobStatus, Organization, ProcessingJob, User


class DatabaseModelTests(unittest.TestCase):
    def test_expected_tables_are_registered(self) -> None:
        self.assertEqual(
            set(Base.metadata.tables),
            {
                "organizations",
                "users",
                "documents",
                "processing_jobs",
                "review_decisions",
                "audit_events",
            },
        )

    def test_every_tenant_owned_table_has_organization_id(self) -> None:
        for table_name in (
            "users",
            "documents",
            "processing_jobs",
            "review_decisions",
            "audit_events",
        ):
            with self.subTest(table=table_name):
                column = Base.metadata.tables[table_name].c.organization_id
                self.assertFalse(column.nullable)

    def test_child_records_use_tenant_scoped_foreign_keys(self) -> None:
        expected_constraints = {
            "documents": {"fk_documents_uploader_tenant"},
            "processing_jobs": {
                "fk_processing_jobs_document_tenant",
                "fk_processing_jobs_requester_tenant",
            },
            "review_decisions": {
                "fk_review_decisions_actor_tenant",
                "fk_review_decisions_document_tenant",
                "fk_review_decisions_job_tenant",
            },
            "audit_events": {"fk_audit_events_actor_tenant"},
        }

        for table_name, expected_names in expected_constraints.items():
            table = Base.metadata.tables[table_name]
            names = {
                constraint.name
                for constraint in table.constraints
                if isinstance(constraint, ForeignKeyConstraint)
                and len(constraint.column_keys) == 2
            }
            with self.subTest(table=table_name):
                self.assertTrue(expected_names.issubset(names))

    def test_processing_idempotency_is_unique_per_organization(self) -> None:
        table = Base.metadata.tables["processing_jobs"]
        unique_columns = {
            tuple(constraint.columns.keys())
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
        }

        self.assertIn(("organization_id", "idempotency_key"), unique_columns)

    def test_structured_results_compile_to_postgresql_jsonb(self) -> None:
        jobs = Base.metadata.tables["processing_jobs"]
        reviews = Base.metadata.tables["review_decisions"]
        audits = Base.metadata.tables["audit_events"]

        for column in (
            jobs.c.extraction_result,
            jobs.c.evidence,
            reviews.c.decision_payload,
            audits.c.safe_metadata,
        ):
            with self.subTest(column=column.name):
                compiled = column.type.dialect_impl(postgresql.dialect())
                self.assertEqual(compiled.__class__.__name__, "_PGJSONB")

    def test_audit_events_have_no_update_or_delete_columns(self) -> None:
        columns = set(Base.metadata.tables["audit_events"].columns.keys())

        self.assertNotIn("updated_at", columns)
        self.assertNotIn("deleted_at", columns)
        self.assertIn("timestamp", columns)
        self.assertIn("safe_metadata", columns)

    def test_database_rejects_cross_tenant_job_reference(self) -> None:
        engine = create_engine("sqlite://")

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(engine)
        organization_a = uuid.uuid4()
        organization_b = uuid.uuid4()
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        document_a = uuid.uuid4()

        with engine.begin() as connection:
            connection.execute(
                Organization.__table__.insert(),
                [
                    {"id": organization_a, "name": "Organization A"},
                    {"id": organization_b, "name": "Organization B"},
                ],
            )
            connection.execute(
                User.__table__.insert(),
                [
                    {
                        "id": user_a,
                        "organization_id": organization_a,
                        "external_subject": "user-a",
                        "email": "user-a@example.com",
                    },
                    {
                        "id": user_b,
                        "organization_id": organization_b,
                        "external_subject": "user-b",
                        "email": "user-b@example.com",
                    },
                ],
            )
            connection.execute(
                Document.__table__.insert(),
                {
                    "id": document_a,
                    "organization_id": organization_a,
                    "uploaded_by_user_id": user_a,
                    "original_filename": "invoice.pdf",
                    "storage_key": f"validated/{organization_a}/{document_a}.pdf",
                    "content_type": "application/pdf",
                    "size_bytes": 1024,
                    "status": DocumentStatus.VALIDATED,
                },
            )

        with self.assertRaises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    ProcessingJob.__table__.insert(),
                    {
                        "organization_id": organization_b,
                        "document_id": document_a,
                        "requested_by_user_id": user_b,
                        "idempotency_key": "cross-tenant-attempt",
                        "status": JobStatus.QUEUED,
                    },
                )


if __name__ == "__main__":
    unittest.main()
