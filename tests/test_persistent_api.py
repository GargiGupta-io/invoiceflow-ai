from __future__ import annotations

import uuid
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v2 import router
from app.auth.claims import VerifiedIdentity
from app.auth.dependencies import get_database, get_token_verifier
from app.db import Base, Organization, User
from app.db.repositories import DocumentRepository, ProcessingJobRepository
from app.db.session import create_database
from app.db.tenant import TenantContext


class StaticTokenVerifier:
    def __init__(self, identity: VerifiedIdentity) -> None:
        self.identity = identity

    def verify(self, _token: str) -> VerifiedIdentity:
        return self.identity


class PersistentApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = create_database(database_url="sqlite://")
        Base.metadata.create_all(self.database.engine)
        self.organization_a = uuid.uuid4()
        self.organization_b = uuid.uuid4()
        self.user_a = uuid.uuid4()
        self.user_b = uuid.uuid4()
        self.subject_a = "cognito-user-a"
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
                        email="user-a@example.com",
                    ),
                    User(
                        id=self.user_b,
                        organization_id=self.organization_b,
                        external_subject="cognito-user-b",
                        email="user-b@example.com",
                    ),
                ]
            )

        self.document_a, self.job_a = self._create_case(self.tenant_a, "a")
        self.document_b, self.job_b = self._create_case(self.tenant_b, "b")
        self.second_document_a, self.second_job_a = self._create_case(self.tenant_a, "a-second")

        identity = VerifiedIdentity(
            subject=self.subject_a,
            organization_id=self.organization_a,
            username="user-a@example.com",
            scopes=frozenset({"invoiceflow.read", "invoiceflow.review"}),
        )
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[get_database] = lambda: self.database
        self.app.dependency_overrides[get_token_verifier] = lambda: StaticTokenVerifier(identity)
        self.client = TestClient(self.app)
        self.headers = {"Authorization": "Bearer valid-token"}

    def tearDown(self) -> None:
        self.database.dispose()

    def _create_case(self, tenant: TenantContext, suffix: str):
        with self.database.transaction() as session:
            document = DocumentRepository(session, tenant).create(
                original_filename=f"invoice-{suffix}.pdf",
                storage_key=f"validated/{tenant.organization_id}/invoice-{suffix}.pdf",
                content_type="application/pdf",
                size_bytes=4096,
                page_count=3,
            )
            job = ProcessingJobRepository(session, tenant).get_or_create(
                document_id=document.id,
                idempotency_key=f"process-{suffix}",
            )
            return document, job

    def test_current_identity_uses_internal_user_id(self) -> None:
        response = self.client.get("/v2/me", headers=self.headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.json()["organization_id"], str(self.organization_a))
        self.assertEqual(response.json()["actor_id"], str(self.user_a))

    def test_document_history_only_returns_current_tenant(self) -> None:
        response = self.client.get("/v2/documents", headers=self.headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        payload = response.json()
        self.assertEqual(payload["count"], 2)
        returned_ids = {item["id"] for item in payload["items"]}
        self.assertEqual(
            returned_ids,
            {str(self.document_a.id), str(self.second_document_a.id)},
        )
        self.assertNotIn(str(self.document_b.id), returned_ids)

    def test_cross_tenant_document_returns_not_found(self) -> None:
        response = self.client.get(
            f"/v2/documents/{self.document_b.id}",
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"]["code"], "resource_not_found")

    def test_document_detail_includes_owned_job_metadata(self) -> None:
        response = self.client.get(
            f"/v2/documents/{self.document_a.id}",
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        payload = response.json()
        self.assertEqual(payload["document"]["id"], str(self.document_a.id))
        self.assertEqual(payload["processing_jobs"][0]["id"], str(self.job_a.id))
        self.assertNotIn("extraction_result", payload["processing_jobs"][0])
        self.assertNotIn("evidence", payload["processing_jobs"][0])
        self.assertIsNone(payload["case_result"])

    def test_document_detail_exposes_safe_completed_case_result(self) -> None:
        with self.database.transaction() as session:
            jobs = ProcessingJobRepository(session, self.tenant_a)
            jobs.claim(job_id=self.job_a.id, document_id=self.document_a.id)
            jobs.complete(
                job_id=self.job_a.id,
                document_id=self.document_a.id,
                extraction_result={
                    "workflow_result": {
                        "workflow_type": "accounts_payable",
                        "extraction": {"vendor_name": "Northstar Supplies"},
                        "ap_decision": {
                            "recommendation": "review",
                            "reviewer_summary": "A purchase order needs review.",
                        },
                    },
                    "route": {"workflow_type": "accounts_payable"},
                    "policy_assessment": {"reason_codes": ["po_required_missing"]},
                    "human_review": {"required": True, "blocking": True},
                    "agent_tool_trace": [{"tool": "extract_invoice_fields"}],
                    "stage_latencies_ms": {"extraction": 12.5},
                },
                evidence=[
                    {
                        "source_id": "AP-APPROVAL-001",
                        "source_title": "Approval policy",
                        "excerpt": "A purchase order is required.",
                    }
                ],
            )

        response = self.client.get(
            f"/v2/documents/{self.document_a.id}",
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 200)
        case_result = response.json()["case_result"]
        self.assertEqual(case_result["processing_job_id"], str(self.job_a.id))
        self.assertEqual(
            case_result["workflow_result"]["extraction"]["vendor_name"],
            "Northstar Supplies",
        )
        self.assertEqual(case_result["evidence"][0]["source_id"], "AP-APPROVAL-001")
        self.assertNotIn("idempotency_key", case_result)

    def test_review_creation_persists_review_and_safe_audit(self) -> None:
        response = self.client.post(
            f"/v2/documents/{self.document_a.id}/reviews",
            headers=self.headers,
            json={
                "processing_job_id": str(self.job_a.id),
                "action": "approved",
                "reason": "Policy checks passed.",
                "reviewer_note": "Approved for payment.",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["actor_user_id"], str(self.user_a))

        reviews_response = self.client.get(
            f"/v2/documents/{self.document_a.id}/reviews",
            headers=self.headers,
        )
        audit_response = self.client.get(
            f"/v2/documents/{self.document_a.id}/audit",
            headers=self.headers,
        )
        reviews = reviews_response.json()
        audit = audit_response.json()
        self.assertEqual(len(reviews), 1)
        self.assertEqual(audit[0]["action"], "review.approved")
        self.assertNotIn("reviewer_note", audit[0]["safe_metadata"])
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(reviews_response.headers["cache-control"], "no-store")
        self.assertEqual(audit_response.headers["cache-control"], "no-store")

    def test_review_rejects_job_from_another_document(self) -> None:
        response = self.client.post(
            f"/v2/documents/{self.document_a.id}/reviews",
            headers=self.headers,
            json={
                "processing_job_id": str(self.second_job_a.id),
                "action": "rejected",
                "reason": "Wrong case linkage.",
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"]["code"], "resource_not_found")

    def test_persistent_routes_require_authentication(self) -> None:
        response = self.client.get("/v2/documents")

        self.assertEqual(response.status_code, 401)

    def test_review_creation_requires_review_scope(self) -> None:
        read_only_identity = VerifiedIdentity(
            subject=self.subject_a,
            organization_id=self.organization_a,
            username="user-a@example.com",
            scopes=frozenset({"invoiceflow.read"}),
        )
        self.app.dependency_overrides[get_token_verifier] = lambda: StaticTokenVerifier(
            read_only_identity
        )

        response = self.client.post(
            f"/v2/documents/{self.document_a.id}/reviews",
            headers=self.headers,
            json={
                "processing_job_id": str(self.job_a.id),
                "action": "approved",
                "reason": "Policy checks passed.",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"]["code"], "insufficient_scope")


if __name__ == "__main__":
    unittest.main()
