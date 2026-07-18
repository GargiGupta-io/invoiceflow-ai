from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditEvent
from app.db.repositories.base import TenantRepository
from app.db.tenant import TenantContext


class AuditEventRepository(TenantRepository):
    def __init__(self, session: Session, tenant: TenantContext) -> None:
        super().__init__(session, tenant)

    def append(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: str,
        request_id: str,
        safe_metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            organization_id=self.tenant.organization_id,
            actor_id=self.tenant.actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
            safe_metadata=dict(safe_metadata or {}),
        )
        self.session.add(event)
        self.session.flush()
        return event

    def list_for_resource(self, resource_type: str, resource_id: str) -> list[AuditEvent]:
        statement = (
            select(AuditEvent)
            .where(
                AuditEvent.organization_id == self.tenant.organization_id,
                AuditEvent.resource_type == resource_type,
                AuditEvent.resource_id == resource_id,
            )
            .order_by(AuditEvent.timestamp.desc())
        )
        return list(self.session.scalars(statement))
