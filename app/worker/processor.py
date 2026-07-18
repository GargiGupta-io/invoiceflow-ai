from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.orchestrator import run_workflow_from_upload


@dataclass(frozen=True)
class ProcessedDocument:
    result: dict[str, Any]
    evidence: list[dict[str, Any]]


class DocumentProcessor(Protocol):
    def process(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> ProcessedDocument: ...


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
        payload = run_workflow_from_upload(
            filename=filename,
            content=content,
            extractor_mode=self.extractor_mode,
        )
        audit = payload.get("audit_trail") or {}
        context = payload.get("grounded_context") or {}
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
        )
