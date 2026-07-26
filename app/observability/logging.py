from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Mapping


REDACTED = "[REDACTED]"
SENSITIVE_KEY_PARTS = {
    "api_key",
    "authorization",
    "cookie",
    "document_content",
    "password",
    "presigned_url",
    "receipt_handle",
    "secret",
    "token",
}
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_SECRET_VALUE_PATTERN = re.compile(
    r"(?i)\b(authorization|cookie|password|secret|token|api[_-]?key)\s*[:=]\s*([^\s,;]+)"
)
_SIGNED_QUERY_PATTERN = re.compile(r"(?i)(https?://[^\s?]+)\?[^\s]+")


def _normalized_key(key: object) -> str:
    return str(key).lower().replace("-", "_")


def _is_sensitive_key(key: object) -> bool:
    normalized = _normalized_key(key)
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def _redact_text(value: str) -> str:
    value = _BEARER_PATTERN.sub(f"Bearer {REDACTED}", value)
    value = _SECRET_VALUE_PATTERN.sub(lambda match: f"{match.group(1)}={REDACTED}", value)
    return _SIGNED_QUERY_PATTERN.sub(lambda match: f"{match.group(1)}?{REDACTED}", value)


def redact(value: Any, *, key: object | None = None) -> Any:
    if key is not None and _is_sensitive_key(key):
        return REDACTED
    if isinstance(value, Mapping):
        return {str(item_key): redact(item, key=item_key) for item_key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)


class SensitiveDataFilter(logging.Filter):
    """Redact structured fields before any handler receives the record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.event_fields = redact(getattr(record, "event_fields", {}))
        return True


class JsonEventFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "event": getattr(record, "event", "application_log"),
        }
        fields = redact(getattr(record, "event_fields", {}))
        if isinstance(fields, Mapping):
            payload.update(fields)
        if record.exc_info:
            payload.setdefault("error_category", "unhandled_exception")
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)


class RuntimeEventLogger:
    def __init__(
        self,
        logger: logging.Logger,
        *,
        service: str,
        environment: str,
        metric_namespace: str = "InvoiceFlow",
    ) -> None:
        self.logger = logger
        self.service = service
        self.environment = environment
        self.metric_namespace = metric_namespace

    def emit(self, event: str, *, level: int = logging.INFO, **fields: Any) -> None:
        self.logger.log(
            level,
            event,
            extra={"event": event, "event_fields": fields},
        )

    def worker_result(
        self,
        *,
        outcome: str,
        duration_ms: float,
        request_id: object | None,
        job_id: object | None,
        message_id: str | None,
        receive_count: int | None,
        error_category: str | None = None,
        error_code: str | None = None,
    ) -> None:
        successful = outcome in {"completed", "already_completed"}
        failed = outcome in {
            "ack_failed",
            "invalid_message",
            "permanent_failure",
            "retry_exhausted",
            "retry_scheduled",
            "unknown_job",
        }
        status = "success" if successful else "failed" if failed else "ignored"
        fields: dict[str, Any] = {
            "service": self.service,
            "environment": self.environment,
            "status": status,
            "outcome": outcome,
            "duration_ms": round(duration_ms, 3),
            "request_id": str(request_id) if request_id else None,
            "job_id": str(job_id) if job_id else None,
            "message_id": message_id,
            "receive_count": receive_count,
            "error_category": error_category,
            "error_code": error_code,
            "WorkerCycles": 1,
            "WorkerSuccesses": int(successful),
            "WorkerFailures": int(failed),
            "WorkerDuration": round(duration_ms, 3),
            "_aws": {
                "Timestamp": int(time.time() * 1000),
                "CloudWatchMetrics": [
                    {
                        "Namespace": self.metric_namespace,
                        "Dimensions": [["service", "environment"]],
                        "Metrics": [
                            {"Name": "WorkerCycles", "Unit": "Count"},
                            {"Name": "WorkerSuccesses", "Unit": "Count"},
                            {"Name": "WorkerFailures", "Unit": "Count"},
                            {"Name": "WorkerDuration", "Unit": "Milliseconds"},
                        ],
                    }
                ],
            },
        }
        self.emit(
            "document_processed" if outcome == "completed" else "document_worker_cycle",
            level=logging.WARNING if failed else logging.INFO,
            **fields,
        )


def configure_logging(*, level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.addFilter(SensitiveDataFilter())
    handler.setFormatter(JsonEventFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
