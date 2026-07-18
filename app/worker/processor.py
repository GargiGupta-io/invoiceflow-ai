from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.ingest import IngestionError
from app.orchestrator import run_workflow_from_upload


@dataclass(frozen=True)
class ProcessedDocument:
    result: dict[str, Any]
    evidence: list[dict[str, Any]]
    pages: list[dict[str, Any]] = field(default_factory=list)


class DocumentProcessor(Protocol):
    def process(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> ProcessedDocument: ...


class PermanentDocumentProcessingError(RuntimeError):
    """The document cannot succeed without changing the input or processor."""

    def __init__(self, code: str, category: str = "document") -> None:
        super().__init__(code)
        self.code = code
        self.category = category


class InvoiceFlowDocumentProcessor:
    def __init__(self, *, extractor_mode: str = "heuristic") -> None:
        self.extractor_mode = extractor_mode

    def process(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> ProcessedDocument:
        if content_type not in {
            "application/pdf",
            "image/png",
            "image/jpeg",
            "text/plain",
            "text/markdown",
        }:
            raise PermanentDocumentProcessingError("document_type_unsupported")
        try:
            payload = run_workflow_from_upload(
                filename=filename,
                content=content,
                extractor_mode=self.extractor_mode,
                include_document_pages=True,
            )
        except IngestionError:
            raise PermanentDocumentProcessingError("document_ingestion_failed") from None
        audit = payload.get("audit_trail") or {}
        context = payload.get("grounded_context") or {}
        pages = payload.pop("_document_pages", [])
        result = {
            "workflow_result": payload.get("workflow_result") or {},
            "route": payload.get("route") or {},
            "policy_assessment": payload.get("policy_assessment") or {},
            "human_review": audit.get("human_review") or {},
            "agent_tool_trace": audit.get("agent_tool_trace") or [],
            "stage_latencies_ms": audit.get("stage_latencies_ms") or {},
            "content_type": content_type,
        }
        evidence = context.get("evidence_payloads") or []
        return ProcessedDocument(
            result=result,
            evidence=[dict(item) for item in evidence if isinstance(item, dict)],
            pages=[dict(item) for item in pages if isinstance(item, dict)],
        )
