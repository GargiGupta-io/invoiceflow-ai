from __future__ import annotations

import unittest
import uuid
from unittest.mock import MagicMock

from sqlalchemy.dialects import postgresql

from app.db import Base, DocumentPage, Organization, User
from app.db.repositories import (
    DocumentPageInput,
    DocumentPageRepository,
    DocumentRepository,
    TenantResourceNotFound,
)
from app.db.session import create_database
from app.db.tenant import TenantContext


class DocumentPageRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = create_database(database_url="sqlite://")
        Base.metadata.create_all(self.database.engine)
        self.organization_a = uuid.uuid4()
        self.organization_b = uuid.uuid4()
        self.user_a = uuid.uuid4()
        self.user_b = uuid.uuid4()
        self.tenant_a = TenantContext(self.organization_a, self.user_a)
        self.tenant_b = TenantContext(self.organization_b, self.user_b)
        with self.database.transaction() as session:
            session.add_all(
                [
                    Organization(id=self.organization_a, name="Organization A"),
                    Organization(id=self.organization_b, name="Organization B"),
                    User(
                        id=self.user_a,
                        organization_id=self.organization_a,
                        external_subject="page-user-a",
                        email="page-a@example.com",
                    ),
                    User(
                        id=self.user_b,
                        organization_id=self.organization_b,
                        external_subject="page-user-b",
                        email="page-b@example.com",
                    ),
                ]
            )
        self.document_a = self._create_document(self.tenant_a, "a")
        self.document_b = self._create_document(self.tenant_b, "b")

    def tearDown(self) -> None:
        self.database.dispose()

    def _create_document(self, tenant: TenantContext, suffix: str):
        with self.database.transaction() as session:
            return DocumentRepository(session, tenant).create(
                original_filename=f"invoice-{suffix}.pdf",
                storage_key=f"validated/{tenant.organization_id}/invoice-{suffix}.pdf",
                content_type="application/pdf",
                size_bytes=2048,
                page_count=2,
            )

    def test_pages_are_ordered_and_replaceable(self) -> None:
        with self.database.transaction() as session:
            pages = DocumentPageRepository(session, self.tenant_a)
            pages.replace_for_document(
                self.document_a.id,
                [
                    DocumentPageInput(2, "Approval threshold USD 5000", "ocr"),
                    DocumentPageInput(1, "Invoice INV-101", "native"),
                ],
            )
            first = pages.list_for_document(self.document_a.id)
            pages.replace_for_document(
                self.document_a.id,
                [DocumentPageInput(1, "Replacement page", "native")],
            )
            replaced = pages.list_for_document(self.document_a.id)

        self.assertEqual([page.page_number for page in first], [1, 2])
        self.assertEqual([page.text_content for page in replaced], ["Replacement page"])

    def test_search_returns_ranked_pages_only_for_current_tenant(self) -> None:
        with self.database.transaction() as session:
            DocumentPageRepository(session, self.tenant_a).replace_for_document(
                self.document_a.id,
                [DocumentPageInput(2, "A purchase order is required for payment.", "ocr")],
            )
            DocumentPageRepository(session, self.tenant_b).replace_for_document(
                self.document_b.id,
                [DocumentPageInput(1, "Secret purchase order for another tenant.", "native")],
            )

        with self.database.transaction() as session:
            hits = DocumentPageRepository(session, self.tenant_a).search("purchase order")

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].document_id, self.document_a.id)
        self.assertEqual(hits[0].page_number, 2)
        self.assertIn("purchase order", hits[0].excerpt.lower())

    def test_cross_tenant_page_listing_returns_not_found(self) -> None:
        with self.database.transaction() as session:
            with self.assertRaises(TenantResourceNotFound):
                DocumentPageRepository(session, self.tenant_a).list_for_document(
                    self.document_b.id
                )

    def test_postgresql_search_uses_full_text_query_and_tenant_filter(self) -> None:
        session = MagicMock()
        session.get_bind.return_value.dialect.name = "postgresql"
        page = DocumentPage(
            organization_id=self.organization_a,
            document_id=self.document_a.id,
            page_number=1,
            text_content="Purchase order PO-118",
            extraction_method="native",
            warnings=[],
        )
        session.execute.return_value = [(page, 0.75)]

        hits = DocumentPageRepository(session, self.tenant_a).search("purchase order")
        statement = session.execute.call_args.args[0]
        compiled = str(
            statement.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )

        self.assertEqual(hits[0].score, 0.75)
        self.assertIn("to_tsvector", compiled)
        self.assertIn("websearch_to_tsquery", compiled)
        self.assertIn("document_pages.organization_id", compiled)


if __name__ == "__main__":
    unittest.main()
