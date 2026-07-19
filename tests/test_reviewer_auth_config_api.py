from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v2 import router
from app.config import Settings, get_settings


class ReviewerAuthConfigApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_unconfigured_browser_auth_returns_safe_disabled_state(self) -> None:
        self.app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)

        response = self.client.get("/v2/auth/config")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(
            response.json(),
            {
                "configured": False,
                "issuer": None,
                "client_id": None,
                "authorization_endpoint": None,
                "token_endpoint": None,
                "logout_endpoint": None,
                "jwks_uri": None,
                "redirect_uri": None,
                "post_logout_redirect_uri": None,
                "scopes": [],
            },
        )

    def test_configured_browser_auth_exposes_public_oidc_values_only(self) -> None:
        settings = Settings(
            _env_file=None,
            auth_issuer="https://issuer.example.com/pool",
            auth_client_id="public-browser-client",
            auth_browser_domain="https://login.example.com/",
            auth_redirect_uri="https://app.example.com/reviewer/callback",
            auth_logout_uri="https://app.example.com/reviewer/",
        )
        self.app.dependency_overrides[get_settings] = lambda: settings

        response = self.client.get("/v2/auth/config")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["configured"])
        self.assertEqual(payload["client_id"], "public-browser-client")
        self.assertEqual(
            payload["authorization_endpoint"],
            "https://login.example.com/oauth2/authorize",
        )
        self.assertEqual(payload["token_endpoint"], "https://login.example.com/oauth2/token")
        self.assertEqual(payload["logout_endpoint"], "https://login.example.com/logout")
        self.assertIn("invoiceflow/read", payload["scopes"])
        self.assertNotIn("organization_claim", payload)
        self.assertNotIn("secret", str(payload).lower())


if __name__ == "__main__":
    unittest.main()
