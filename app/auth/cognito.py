from __future__ import annotations

import uuid
from typing import Any

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientError, PyJWTError

from app.auth.claims import VerifiedIdentity


class TokenVerificationError(ValueError):
    """A token failed cryptographic or required-claim validation."""


class CognitoTokenVerifier:
    def __init__(
        self,
        *,
        issuer: str,
        client_id: str,
        organization_claim: str = "custom:organization_id",
        jwks_cache_seconds: int = 300,
        jwks_timeout_seconds: float = 5,
        clock_skew_seconds: int = 30,
        jwk_client: PyJWKClient | None = None,
    ) -> None:
        normalized_issuer = issuer.rstrip("/")
        if not normalized_issuer.startswith("https://"):
            raise ValueError("Cognito issuer must use HTTPS.")
        if not client_id.strip():
            raise ValueError("Cognito client ID is required.")

        self.issuer = normalized_issuer
        self.client_id = client_id
        self.organization_claim = organization_claim
        self.clock_skew_seconds = clock_skew_seconds
        self.jwk_client = jwk_client or PyJWKClient(
            f"{self.issuer}/.well-known/jwks.json",
            cache_jwk_set=True,
            lifespan=jwks_cache_seconds,
            cache_keys=True,
            timeout=jwks_timeout_seconds,
        )

    def verify(self, token: str) -> VerifiedIdentity:
        try:
            signing_key = self.jwk_client.get_signing_key_from_jwt(token)
            claims: dict[str, Any] = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=self.issuer,
                leeway=self.clock_skew_seconds,
                options={
                    "verify_aud": False,
                    "require": [
                        "client_id",
                        "exp",
                        "iat",
                        "iss",
                        "sub",
                        "token_use",
                    ],
                },
            )
        except (PyJWTError, PyJWKClientError, ValueError) as error:
            raise TokenVerificationError("Access token is invalid.") from error

        if claims.get("token_use") != "access":
            raise TokenVerificationError("Access token is invalid.")
        if claims.get("client_id") != self.client_id:
            raise TokenVerificationError("Access token is invalid.")

        organization_value = claims.get(self.organization_claim)
        try:
            organization_id = uuid.UUID(str(organization_value))
        except (TypeError, ValueError, AttributeError) as error:
            raise TokenVerificationError("Access token is invalid.") from error

        scope_value = claims.get("scope", "")
        scopes = frozenset(str(scope_value).split())
        username_value = claims.get("username")
        return VerifiedIdentity(
            subject=str(claims["sub"]),
            organization_id=organization_id,
            username=str(username_value) if username_value is not None else None,
            scopes=scopes,
        )
