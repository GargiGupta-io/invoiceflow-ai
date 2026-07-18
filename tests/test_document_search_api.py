from __future__ import annotations

import unittest
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v2 import router
from app.auth.claims import VerifiedIdentity
from app.auth.dependencies import get_database, get_token_verifier
from app.db import Base, Organization, User
from app.db.repositories import DocumentPageInput, DocumentPageRepository, DocumentRepository
from app.db.session import create_database
from app.db.tenant import TenantContext


class StaticTokenVerifier:
    def __init__(self, identity: VerifiedIdentity) -> None:
        self.identity = identity

    def verify(self, _token: str) -> VerifiedIdentity:
        return self.identity


class DocumentSearchApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = create_database(database_url="sqlite://")
        Base.metadata.create_all(self.database.engine)
        self.organization_a = uuid.uuid4()
        self.organization_b = uuid.uuid4()
        self.user_a = uuid.uuid4()
        self.user_b = uuid.uuid4()
        self.subject_a = "search-user-a"
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
                        external_subject=self.subject_a,
                        email="search-a@example.com",
                    ),
                    User(
                        id=self.user_b,
                        organization_id=self.organization_b,
                        external_subject="search-user-b",
                        email="search-b@example.com",
                    ),
                ]
            )
        self.document_a = self._create_document(
            self.tenant_a,
            "a",
            "Purchase order PO-118 is required before approval.",
        )
        self.document_b = self._create_document(
            self.tenant_b,
            "b",
            "Another tenant has purchase order PO-999.",
        )
        identity = VerifiedIdentity(
            subject=self.subject_a,
            organization_id=self.organization_a,
            username="search-a@example.com",
            scopes=frozenset({"invoiceflow.read"}),
        )
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[get_database] = lambda: self.database
        self.app.dependency_overrides[get_token_verifier] = lambda: StaticTokenVerifier(identity)
        self.client = TestClient(self.app)
        self.headers = {"Authorization": "Bearer valid-read-token"}

    def tearDown(self) -> None:
        self.database.dispose()

    def _create_document(self, tenant: TenantContext, suffix: str, text: str):
        with self.database.transaction() as session:
            document = DocumentRepository(session, tenant).create(
                original_filename=f"invoice-{suffix}.pdf",
                storage_key=f"validated/{tenant.organization_id}/invoice-{suffix}.pdf",
                content_type="application/pdf",
                size_bytes=2048,
                page_count=1,
            )
            DocumentPageRepository(session, tenant).replace_for_document(
                document.id,
                [DocumentPageInput(1, text, "native")],
            )
            return document

    def test_search_returns_page_location_and_private_access_path(self) -> None:
        response = self.client.post(
            "/v2/search",
            json={"query": "purchase order"},
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        hit = payload["items"][0]
        self.assertEqual(hit["document_id"], str(self.document_a.id))
        self.assertEqual(hit["page_number"], 1)
        self.assertEqual(hit["page_fragment"], "#page=1")
        self.assertEqual(
            hit["access_path"],
            f"/v2/documents/{self.document_a.id}/access",
        )
        self.assertNotIn(str(self.document_b.id), response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_owned_pages_are_readable_but_cross_tenant_pages_are_hidden(self) -> None:
        owned = self.client.get(
            f"/v2/documents/{self.document_a.id}/pages",
            headers=self.headers,
        )
        foreign = self.client.get(
            f"/v2/documents/{self.document_b.id}/pages",
            headers=self.headers,
        )

        self.assertEqual(owned.status_code, 200)
        self.assertEqual(owned.json()["items"][0]["page_number"], 1)
        self.assertEqual(owned.headers["cache-control"], "no-store")
        self.assertEqual(foreign.status_code, 404)

    def test_search_requires_authentication_and_a_bounded_query(self) -> None:
        unauthenticated = self.client.post(
            "/v2/search",
            json={"query": "purchase order"},
        )
        too_short = self.client.post(
            "/v2/search",
            json={"query": "p"},
            headers=self.headers,
        )

        self.assertEqual(unauthenticated.status_code, 401)
        self.assertEqual(too_short.status_code, 422)


if __name__ == "__main__":
    unittest.main()
