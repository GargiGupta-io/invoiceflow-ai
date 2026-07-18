from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Mapping, Protocol


StorageBody = bytes | BinaryIO


@dataclass(frozen=True)
class StoredObject:
    bucket: str
    key: str
    etag: str | None = None
    version_id: str | None = None


class StorageOperationError(RuntimeError):
    """A safe storage failure that does not expose object or provider details."""


class ObjectStorage(Protocol):
    def upload_quarantined(
        self,
        *,
        key: str,
        content: StorageBody,
        content_type: str,
        metadata: Mapping[str, str] | None = None,
    ) -> StoredObject: ...

    def promote(self, *, source_key: str, destination_key: str) -> StoredObject: ...

    def read(self, *, key: str, max_bytes: int) -> bytes: ...

    def create_download_url(self, *, key: str, expires_in_seconds: int) -> str: ...

    def delete(self, *, key: str) -> None: ...
