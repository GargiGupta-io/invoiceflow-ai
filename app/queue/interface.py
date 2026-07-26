from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any, Protocol


class QueueOperationError(RuntimeError):
    """A safe queue failure that does not expose provider details."""


class QueueMessageValidationError(ValueError):
    """A queue message does not match the supported processing contract."""


@dataclass(frozen=True)
class ProcessingMessage:
    job_id: uuid.UUID
    document_id: uuid.UUID
    organization_id: uuid.UUID
    request_id: uuid.UUID
    schema_version: int = 1
    event_type: str = "document.processing.requested"

    @classmethod
    def from_body(cls, body: str) -> ProcessingMessage:
        try:
            payload: Any = json.loads(body)
        except (TypeError, json.JSONDecodeError):
            raise QueueMessageValidationError("Processing message is not valid JSON.") from None

        expected_fields = {
            "document_id",
            "event_type",
            "job_id",
            "organization_id",
            "request_id",
            "schema_version",
        }
        if not isinstance(payload, dict) or set(payload) != expected_fields:
            raise QueueMessageValidationError("Processing message fields are invalid.")
        if payload["schema_version"] != 1 or isinstance(payload["schema_version"], bool):
            raise QueueMessageValidationError("Processing message schema is unsupported.")
        if payload["event_type"] != "document.processing.requested":
            raise QueueMessageValidationError("Processing message event is unsupported.")

        try:
            return cls(
                job_id=uuid.UUID(payload["job_id"]),
                document_id=uuid.UUID(payload["document_id"]),
                organization_id=uuid.UUID(payload["organization_id"]),
                request_id=uuid.UUID(payload["request_id"]),
            )
        except (AttributeError, TypeError, ValueError):
            raise QueueMessageValidationError("Processing message identifiers are invalid.") from None

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


@dataclass(frozen=True)
class ReceivedQueueMessage:
    message_id: str
    receipt_handle: str
    body: str
    receive_count: int


class ProcessingQueue(Protocol):
    def check_health(self) -> None: ...

    def send(self, message: ProcessingMessage) -> QueueDispatchReceipt: ...

    def receive_one(
        self,
        *,
        wait_time_seconds: int,
        visibility_timeout_seconds: int,
    ) -> ReceivedQueueMessage | None: ...

    def delete(self, *, receipt_handle: str) -> None: ...

    def change_visibility(
        self,
        *,
        receipt_handle: str,
        visibility_timeout_seconds: int,
    ) -> None: ...
