from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentObjectKeys:
    quarantine_key: str
    validated_key: str


def normalize_storage_prefix(prefix: str) -> str:
    normalized = prefix.strip().strip("/")
    segments = normalized.split("/")
    if not normalized or any(segment in {"", ".", ".."} for segment in segments):
        raise ValueError("Storage prefix must contain safe, non-empty path segments.")
    return normalized


def validate_document_key(*, key: str, prefix: str) -> None:
    normalized_prefix = normalize_storage_prefix(prefix)
    segments = key.split("/")
    prefix_segments = normalized_prefix.split("/")
    if segments[: len(prefix_segments)] != prefix_segments:
        raise ValueError("Object key is outside the required storage prefix.")
    if len(segments) != len(prefix_segments) + 2:
        raise ValueError("Object key must identify one tenant and one document.")
    try:
        uuid.UUID(segments[-2])
        uuid.UUID(segments[-1])
    except ValueError:
        raise ValueError("Object key must use UUID tenant and document identifiers.") from None


def build_document_keys(
    *,
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    quarantine_prefix: str = "quarantine",
    validated_prefix: str = "validated",
) -> DocumentObjectKeys:
    quarantine = normalize_storage_prefix(quarantine_prefix)
    validated = normalize_storage_prefix(validated_prefix)
    tenant_path = f"{organization_id}/{document_id}"
    return DocumentObjectKeys(
        quarantine_key=f"{quarantine}/{tenant_path}",
        validated_key=f"{validated}/{tenant_path}",
    )
