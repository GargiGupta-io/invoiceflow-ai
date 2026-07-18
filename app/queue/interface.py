from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Protocol


class QueueOperationError(RuntimeError):
    """A safe queue failure that does not expose provider details."""


@dataclass(frozen=True)
class ProcessingMessage:
    job_id: uuid.UUID
    document_id: uuid.UUID
    organization_id: uuid.UUID
    request_id: uuid.UUID
    schema_version: int = 1
    event_type: str = "document.processing.requested"

    def to_body(self) -> str:
        return json.dumps(
            {
                "document_id": str(self.document_id),
                "event_type": self.event_type,
                "job_id": str(self.job_id),
                "organization_id": str(self.organization_id),
                "request_id": str(self.request_id),
                "schema_version": self.schema_version,
            },
            separators=(",", ":"),
            sort_keys=True,
        )


@dataclass(frozen=True)
class QueueDispatchReceipt:
    message_id: str


class ProcessingQueue(Protocol):
    def send(self, message: ProcessingMessage) -> QueueDispatchReceipt: ...
