from __future__ import annotations

import time
import uuid
import unittest
from types import SimpleNamespace

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth.claims import VerifiedIdentity
from app.auth.cognito import CognitoTokenVerifier, TokenVerificationError
from app.auth.dependencies import get_database, get_token_verifier, require_tenant
from app.db import Base, Organization, User
from app.db.session import create_database
from app.db.tenant import TenantContext


class StaticJwkClient:
    def __init__(self, public_key) -> None:
        self.public_key = public_key

    def get_signing_key_from_jwt(self, _token: str):
        return SimpleNamespace(key=self.public_key)


class StaticTokenVerifier:
    def __init__(self, identity: VerifiedIdentity | None = None, *, valid: bool = True) -> None:
        self.identity = identity
        self.valid = valid

    def verify(self, _token: str) -> VerifiedIdentity:
        if not self.valid or self.identity is None:
            raise TokenVerificationError("Access token is invalid.")
        return self.identity


class CognitoTokenVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.public_key = cls.private_key.public_key()
        cls.issuer = "https://cognito-idp.ap-south-1.amazonaws.com/ap-south-1_TEST"
        cls.client_id = "invoiceflow-test-client"
        cls.organization_id = uuid.uuid4()

    def _token(self, **overrides) -> str:
        now = int(time.time())
        claims = {
            "client_id": self.client_id,
            "custom:organization_id": str(self.organization_id),
            "exp": now + 300,
            "iat": now,
            "iss": self.issuer,
            "scope": "invoiceflow.read invoiceflow.review",
            "sub": "cognito-subject-123",
            "token_use": "access",
            "username": "reviewer@example.com",
        }
        claims.update(overrides)
        return jwt.encode(claims, self.private_key, algorithm="RS256", headers={"kid": "test-key"})

    def _verifier(self) -> CognitoTokenVerifier:
        return CognitoTokenVerifier(
            issuer=self.issuer,
            client_id=self.client_id,
            jwk_client=StaticJwkClient(self.public_key),
        )

    def test_valid_access_token_returns_normalized_identity(self) -> None:
        identity = self._verifier().verify(self._token())

        self.assertEqual(identity.subject, "cognito-subject-123")
        self.assertEqual(identity.organization_id, self.organization_id)
        self.assertIn("invoiceflow.review", identity.scopes)

    def test_id_token_is_rejected(self) -> None:
        with self.assertRaises(TokenVerificationError):
            self._verifier().verify(self._token(token_use="id"))

    def test_wrong_client_is_rejected(self) -> None:
        with self.assertRaises(TokenVerificationError):
            self._verifier().verify(self._token(client_id="another-client"))

    def test_invalid_organization_claim_is_rejected(self) -> None:
        with self.assertRaises(TokenVerificationError):
            self._verifier().verify(self._token(**{"custom:organization_id": "not-a-uuid"}))

    def test_expired_token_is_rejected(self) -> None:
        now = int(time.time())
        with self.assertRaises(TokenVerificationError):
            self._verifier().verify(self._token(exp=now - 120, iat=now - 300))


class AuthenticationDependencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = create_database(database_url="sqlite://")
        Base.metadata.create_all(self.database.engine)
        self.organization_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.subject = "known-cognito-subject"

        with self.database.transaction() as session:
            session.add(Organization(id=self.organization_id, name="Test Organization"))
            session.add(
                User(
                    id=self.user_id,
                    organization_id=self.organization_id,
                    external_subject=self.subject,
                    email="reviewer@example.com",
                )
            )

        self.identity = VerifiedIdentity(
            subject=self.subject,
            organization_id=self.organization_id,
            username="reviewer@example.com",
            scopes=frozenset({"invoiceflow.read"}),
        )
        self.app = FastAPI()

        @self.app.get("/tenant")
        def tenant_route(tenant: TenantContext = Depends(require_tenant)) -> dict[str, str]:
            return {
                "organization_id": str(tenant.organization_id),
                "actor_id": str(tenant.actor_id),
            }

        self.app.dependency_overrides[get_database] = lambda: self.database
        self.app.dependency_overrides[get_token_verifier] = lambda: StaticTokenVerifier(self.identity)
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.database.dispose()

    def test_missing_bearer_token_is_rejected(self) -> None:
        response = self.client.get("/tenant")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["code"], "authentication_required")

    def test_verified_identity_resolves_internal_tenant_context(self) -> None:
        response = self.client.get("/tenant", headers={"Authorization": "Bearer valid-token"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["organization_id"], str(self.organization_id))
        self.assertEqual(response.json()["actor_id"], str(self.user_id))

    def test_unknown_user_is_rejected_without_revealing_lookup_result(self) -> None:
        unknown_identity = VerifiedIdentity(
            subject="unknown-subject",
            organization_id=self.organization_id,
            username=None,
            scopes=frozenset(),
        )
        self.app.dependency_overrides[get_token_verifier] = lambda: StaticTokenVerifier(unknown_identity)

        response = self.client.get("/tenant", headers={"Authorization": "Bearer valid-token"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["code"], "authentication_required")

    def test_inactive_user_is_rejected(self) -> None:
        with self.database.transaction() as session:
            user = session.get(User, self.user_id)
            self.assertIsNotNone(user)
            user.is_active = False

        response = self.client.get("/tenant", headers={"Authorization": "Bearer valid-token"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["code"], "authentication_required")

    def test_invalid_signature_result_is_rejected(self) -> None:
        self.app.dependency_overrides[get_token_verifier] = lambda: StaticTokenVerifier(valid=False)

        response = self.client.get("/tenant", headers={"Authorization": "Bearer invalid-token"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["www-authenticate"], "Bearer")


if __name__ == "__main__":
    unittest.main()
