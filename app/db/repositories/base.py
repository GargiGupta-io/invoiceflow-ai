from __future__ import annotations

import uuid
from typing import Any, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.tenant import TenantContext


ModelT = TypeVar("ModelT")


class TenantResourceNotFound(LookupError):
    """Generic not-found response that does not reveal another tenant's data."""


class IdempotencyConflict(ValueError):
    """The idempotency key already belongs to a different operation."""


class TenantRepository:
    def __init__(self, session: Session, tenant: TenantContext) -> None:
        self.session = session
        self.tenant = tenant

    def _owned_statement(self, model: type[ModelT], resource_id: uuid.UUID) -> Select:
        model_columns: Any = model
        return select(model).where(
            model_columns.id == resource_id,
            model_columns.organization_id == self.tenant.organization_id,
        )

    def _get_owned(self, model: type[ModelT], resource_id: uuid.UUID) -> ModelT | None:
        return self.session.scalar(self._owned_statement(model, resource_id))

    def _require_owned(self, model: type[ModelT], resource_id: uuid.UUID) -> ModelT:
        resource = self._get_owned(model, resource_id)
        if resource is None:
            raise TenantResourceNotFound("Resource was not found.")
        return resource
