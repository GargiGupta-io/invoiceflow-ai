"""Assemble grounded policy context for downstream workflow decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol

from ..rag import (
    KnowledgeIndex,
    RetrievalHit,
    RetrievalRepairReport,
    hits_to_evidence_payloads,
    query_knowledge_index,
    repair_retrieval_if_needed,
)


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
    source_text_excerpt: str
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
    retrieval_repair: RetrievalRepairReport
    summary: str

    def to_dict(self) -> dict:
        return {
            "workflow_type": self.workflow_type,
            "query_text": self.query_text,
            "route_reason": self.route_reason,
            "matched_signals": list(self.matched_signals),
            "retrieval_hits": [asdict(hit) for hit in self.retrieval_hits],
            "evidence_payloads": list(self.evidence_payloads),
            "retrieval_repair": self.retrieval_repair.to_dict(),
            "summary": self.summary,
        }


def assemble_grounded_policy_context(
    extraction: ExtractionLike,
    route: WorkflowRouteLike,
    index: KnowledgeIndex,
    *,
    top_k: int = 12,
) -> GroundedPolicyContext:
    """Build the grounded retrieval context the decision layers will consume."""

    workflow_type = _normalize_workflow_type(route.workflow_type)
    query_text = build_policy_query(extraction, workflow_type)
    workflow_hint = _workflow_hint(workflow_type)
    initial_hits = query_knowledge_index(
        index,
        query_text,
        top_k=min(5, top_k),
        workflow_hint=workflow_hint,
    )
    required_source_ids = infer_required_policy_source_ids(extraction, workflow_type)
    hits, repair_report = repair_retrieval_if_needed(
        index=index,
        query_text=query_text,
        initial_hits=initial_hits,
        required_source_ids=required_source_ids,
        workflow_hint=workflow_hint,
        top_k=top_k,
    )
    evidence_payloads = hits_to_evidence_payloads(hits)

    return GroundedPolicyContext(
        workflow_type=workflow_type,
        query_text=query_text,
        route_reason=route.reason,
        matched_signals=list(route.matched_signals),
        retrieval_hits=hits,
        evidence_payloads=evidence_payloads,
        retrieval_repair=repair_report,
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


def infer_required_policy_source_ids(extraction: ExtractionLike, workflow_type: str) -> list[str]:
    """Infer policy sections that should be present for a well-grounded decision."""

    if workflow_type == "accounts_payable":
        source_ids = ["AP-APPROVAL-001", "AP-POLICY-003"]
        if not extraction.po_number:
            source_ids.append("AP-APPROVAL-002")
        if _excerpt_has_any(extraction.source_text_excerpt, ["duplicate", "resubmitted", "resubmission"]):
            source_ids.append("AP-APPROVAL-003")
        vendor_source_id = _source_id_for_name(
            extraction.vendor_name,
            {
                "northstar office supplies": "VENDOR-001",
                "bluewave logistics": "VENDOR-002",
                "lumina creative studio": "VENDOR-003",
                "quartz cloud systems": "VENDOR-004",
            },
        )
        if vendor_source_id:
            source_ids.append(vendor_source_id)
        return _dedupe(source_ids)

    source_ids = ["AR-ESCALATION-001"]
    document_type = (_string_value(extraction.document_type) or "").lower()
    if document_type == "payment_confirmation":
        source_ids.extend(["AR-ESCALATION-002", "AR-TEMPLATE-004"])
    elif _excerpt_has_any(extraction.source_text_excerpt, ["prior reminders sent: 2", "overdue days: 22", "overdue days: 45"]):
        source_ids.append("AR-TEMPLATE-003")
    else:
        source_ids.append("AR-TEMPLATE-001")

    customer_source_id = _source_id_for_name(
        extraction.customer_name,
        {
            "aster retail": "CUSTOMER-001",
            "horizon health group": "CUSTOMER-002",
            "meridian industrial": "CUSTOMER-003",
        },
    )
    if customer_source_id:
        source_ids.append(customer_source_id)
    return _dedupe(source_ids)


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


def _source_id_for_name(raw_name: str | None, source_ids_by_name: dict[str, str]) -> str | None:
    normalized = (raw_name or "").strip().lower()
    return source_ids_by_name.get(normalized)


def _excerpt_has_any(excerpt: str, markers: list[str]) -> bool:
    lowered = (excerpt or "").lower()
    return any(marker in lowered for marker in markers)


def _dedupe(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = value.strip()
        if item and item not in seen:
            ordered.append(item)
            seen.add(item)
    return ordered
