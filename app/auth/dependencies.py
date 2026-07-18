from __future__ import annotations

from functools import lru_cache
from typing import Callable, Iterator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.claims import TokenVerifier
from app.auth.cognito import CognitoTokenVerifier, TokenVerificationError
from app.config import get_settings
from app.db.repositories import UserRepository
from app.db.session import Database, create_database
from app.db.tenant import TenantContext


bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "authentication_required", "message": "Valid authentication is required."},
        headers={"WWW-Authenticate": "Bearer"},
    )


def _forbidden() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": "insufficient_scope", "message": "Permission is required for this action."},
    )


@lru_cache
def get_database() -> Database:
    return create_database()


@lru_cache
def get_token_verifier() -> TokenVerifier:
    settings = get_settings()
    if not settings.auth_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "authentication_unavailable", "message": "Authentication is not configured."},
        )
    return CognitoTokenVerifier(
        issuer=settings.auth_issuer,
        client_id=settings.auth_client_id,
        organization_claim=settings.auth_organization_claim,
        jwks_cache_seconds=settings.auth_jwks_cache_seconds,
        jwks_timeout_seconds=settings.auth_jwks_timeout_seconds,
        clock_skew_seconds=settings.auth_clock_skew_seconds,
    )


def get_db_session(database: Database = Depends(get_database)) -> Iterator[Session]:
    with database.transaction() as session:
        yield session


def require_tenant(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    verifier: TokenVerifier = Depends(get_token_verifier),
    session: Session = Depends(get_db_session),
) -> TenantContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()

    try:
        identity = verifier.verify(credentials.credentials)
    except TokenVerificationError as error:
        raise _unauthorized() from error

    user = UserRepository(session, identity.organization_id).find_active_by_subject(identity.subject)
    if user is None:
        raise _unauthorized()

    return TenantContext(
        organization_id=identity.organization_id,
        actor_id=user.id,
        scopes=identity.scopes,
    )


def require_scope(required_scope: str) -> Callable[..., TenantContext]:
    def scoped_tenant(tenant: TenantContext = Depends(require_tenant)) -> TenantContext:
        if required_scope not in tenant.scopes:
            raise _forbidden()
        return tenant

    return scoped_tenant


require_read_tenant = require_scope("invoiceflow.read")
require_process_tenant = require_scope("invoiceflow.process")
require_review_tenant = require_scope("invoiceflow.review")
require_upload_tenant = require_scope("invoiceflow.upload")
