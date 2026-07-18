from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentStatus
from app.db.repositories.base import TenantRepository, TenantResourceNotFound
from app.db.tenant import TenantContext


class DocumentRepository(TenantRepository):
    def __init__(self, session: Session, tenant: TenantContext) -> None:
        super().__init__(session, tenant)

    def create(
        self,
        *,
        original_filename: str,
        storage_key: str,
        content_type: str,
        size_bytes: int,
        page_count: int | None = None,
        status: DocumentStatus = DocumentStatus.QUARANTINED,
        retention_until: datetime | None = None,
    ) -> Document:
        document = Document(
            organization_id=self.tenant.organization_id,
            uploaded_by_user_id=self.tenant.actor_id,
            original_filename=original_filename,
            storage_key=storage_key,
            content_type=content_type,
            size_bytes=size_bytes,
            page_count=page_count,
            status=status,
            retention_until=retention_until,
        )
        self.session.add(document)
        self.session.flush()
        return document

    def get(self, document_id: uuid.UUID, *, include_deleted: bool = False) -> Document | None:
        statement = self._owned_statement(Document, document_id)
        if not include_deleted:
            statement = statement.where(Document.deleted_at.is_(None))
        return self.session.scalar(statement)

    def require(self, document_id: uuid.UUID) -> Document:
        document = self.get(document_id)
        if document is None:
            raise TenantResourceNotFound("Resource was not found.")
        return document

    def list_recent(self, *, limit: int = 50) -> list[Document]:
        statement = (
            select(Document)
            .where(
                Document.organization_id == self.tenant.organization_id,
                Document.deleted_at.is_(None),
            )
            .order_by(Document.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))
