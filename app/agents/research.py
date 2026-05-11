"""Assemble grounded policy context for downstream workflow decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol

from ..rag import KnowledgeIndex, RetrievalHit, hits_to_evidence_payloads, query_knowledge_index


class ExtractionLike(Protocol):
    """Small protocol for the extraction fields needed by policy assembly."""

    document_type: Any
    vendor_name: str | None
    customer_name: str | None
    invoice_number: str | None
    po_number: str | None
    amount: float | None
    currency: Any
    due_date: Any
    payment_terms: str | None
    missing_fields: list[str]


class WorkflowRouteLike(Protocol):
    """Small protocol for the routing fields needed by policy assembly."""

    workflow_type: Any
    reason: str
    matched_signals: list[str]


@dataclass(slots=True)
class GroundedPolicyContext:
    """Policy and evidence bundle ready for AP or AR decision agents."""

    workflow_type: str
    query_text: str
    route_reason: str
    matched_signals: list[str]
    retrieval_hits: list[RetrievalHit]
    evidence_payloads: list[dict[str, str]]
    summary: str

    def to_dict(self) -> dict:
        return {
            "workflow_type": self.workflow_type,
            "query_text": self.query_text,
            "route_reason": self.route_reason,
            "matched_signals": list(self.matched_signals),
            "retrieval_hits": [asdict(hit) for hit in self.retrieval_hits],
            "evidence_payloads": list(self.evidence_payloads),
            "summary": self.summary,
        }


def assemble_grounded_policy_context(
    extraction: ExtractionLike,
    route: WorkflowRouteLike,
    index: KnowledgeIndex,
    *,
    top_k: int = 5,
) -> GroundedPolicyContext:
    """Build the grounded retrieval context the decision layers will consume."""

    workflow_type = _normalize_workflow_type(route.workflow_type)
    query_text = build_policy_query(extraction, workflow_type)
    hits = query_knowledge_index(
        index,
        query_text,
        top_k=top_k,
        workflow_hint=_workflow_hint(workflow_type),
    )
    evidence_payloads = hits_to_evidence_payloads(hits)

    return GroundedPolicyContext(
        workflow_type=workflow_type,
        query_text=query_text,
        route_reason=route.reason,
        matched_signals=list(route.matched_signals),
        retrieval_hits=hits,
        evidence_payloads=evidence_payloads,
        summary=_build_context_summary(workflow_type, hits),
    )


def build_policy_query(extraction: ExtractionLike, workflow_type: str) -> str:
    """Create a retrieval-friendly policy query from structured extraction fields."""

    base_parts = [
        f"workflow {workflow_type}",
        f"document type {_string_value(extraction.document_type)}",
    ]

    if workflow_type == "accounts_payable":
        base_parts.extend(
            [
                f"vendor {_fallback_text(extraction.vendor_name, 'unknown')}",
                f"invoice {_fallback_text(extraction.invoice_number, 'unknown')}",
                f"amount {_fallback_number(extraction.amount)}",
                f"currency {_fallback_text(_string_value(extraction.currency), 'unknown')}",
                f"payment terms {_fallback_text(extraction.payment_terms, 'unknown')}",
                "purchase order present" if extraction.po_number else "purchase order missing",
            ]
        )
    else:
        base_parts.extend(
            [
                f"customer {_fallback_text(extraction.customer_name, 'unknown')}",
                f"invoice {_fallback_text(extraction.invoice_number, 'unknown')}",
                f"amount {_fallback_number(extraction.amount)}",
                f"currency {_fallback_text(_string_value(extraction.currency), 'unknown')}",
                f"due date {_fallback_text(_string_value(extraction.due_date), 'unknown')}",
            ]
        )

    missing = ", ".join(extraction.missing_fields) if extraction.missing_fields else "none"
    base_parts.append(f"missing fields {missing}")

    return " | ".join(base_parts)


def _normalize_workflow_type(raw_value: Any) -> str:
    if hasattr(raw_value, "value"):
        return str(raw_value.value)
    return str(raw_value)


def _workflow_hint(workflow_type: str) -> str:
    if workflow_type == "accounts_payable":
        return "ap"
    if workflow_type == "accounts_receivable":
        return "ar"
    return ""


def _build_context_summary(workflow_type: str, hits: list[RetrievalHit]) -> str:
    if not hits:
        return f"No grounded policy evidence was retrieved for {workflow_type}."
    source_ids = ", ".join(hit.source_id for hit in hits[:3])
    return f"Grounded {workflow_type} context assembled from {source_ids}."


def _string_value(raw_value: Any) -> str | None:
    if raw_value is None:
        return None
    if hasattr(raw_value, "value"):
        return str(raw_value.value)
    return str(raw_value)


def _fallback_text(raw_value: str | None, fallback: str) -> str:
    value = (raw_value or "").strip()
    return value or fallback


def _fallback_number(raw_value: float | None) -> str:
    if raw_value is None:
        return "unknown"
    return f"{raw_value:.2f}"
