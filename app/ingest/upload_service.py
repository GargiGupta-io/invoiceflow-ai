from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.models import Document
from app.db.repositories import AuditEventRepository, DocumentRepository
from app.db.tenant import TenantContext
from app.ingest.validation import ValidatedUpload
from app.storage.interface import ObjectStorage, StorageOperationError
from app.storage.keys import build_document_keys


class UploadPersistenceError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class QuarantinedUploadReceipt:
    document: Document
    request_id: uuid.UUID


def persist_quarantined_upload(
    *,
    session: Session,
    tenant: TenantContext,
    storage: ObjectStorage,
    upload: ValidatedUpload,
    quarantine_prefix: str,
    validated_prefix: str,
    retention_days: int = 90,
) -> QuarantinedUploadReceipt:
    if retention_days < 1:
        raise ValueError("Document retention must be at least one day.")
    document_id = uuid.uuid4()
    request_id = uuid.uuid4()
    keys = build_document_keys(
        organization_id=tenant.organization_id,
        document_id=document_id,
        quarantine_prefix=quarantine_prefix,
        validated_prefix=validated_prefix,
    )

    storage_attempted = False
    try:
        storage_attempted = True
        storage.upload_quarantined(
            key=keys.quarantine_key,
            content=upload.content,
            content_type=upload.content_type,
            metadata={
                "document-id": str(document_id),
                "organization-id": str(tenant.organization_id),
                "original-filename": upload.safe_filename,
            },
        )

        document = DocumentRepository(session, tenant).create(
            document_id=document_id,
            original_filename=upload.original_filename,
            storage_key=keys.quarantine_key,
            content_type=upload.content_type,
            size_bytes=upload.size_bytes,
            page_count=upload.page_count,
            retention_until=datetime.now(timezone.utc) + timedelta(days=retention_days),
        )
        AuditEventRepository(session, tenant).append(
            action="document.uploaded",
            resource_type="document",
            resource_id=str(document_id),
            request_id=str(request_id),
            safe_metadata={
                "content_type": upload.content_type,
                "page_count": upload.page_count,
                "size_bytes": upload.size_bytes,
                "storage_state": "quarantine",
                "upload_kind": upload.kind.value,
            },
        )
        session.commit()
    except StorageOperationError:
        session.rollback()
        if storage_attempted:
            _delete_quarantine_object(storage, keys.quarantine_key)
        raise UploadPersistenceError(
            "storage_unavailable",
            "The document could not be stored safely. Try again later.",
        ) from None
    except Exception:
        session.rollback()
        if storage_attempted:
            _delete_quarantine_object(storage, keys.quarantine_key)
        raise UploadPersistenceError(
            "upload_persistence_failed",
            "The document upload could not be saved. Try again later.",
        ) from None

    return QuarantinedUploadReceipt(document=document, request_id=request_id)


def _delete_quarantine_object(storage: ObjectStorage, key: str) -> None:
    try:
        storage.delete(key=key)
    except Exception:
        pass
