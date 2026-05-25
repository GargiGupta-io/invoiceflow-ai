"""Build an explicit agent/tool trace for finance workflow runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from ..schemas.decision import APDecision, ARDecision, ApprovalRecommendation, EscalationLevel
from ..schemas.invoice import InvoiceExtraction
from ..agents.research import GroundedPolicyContext
from .router import WorkflowRoute


@dataclass(slots=True)
class AgentToolTrace:
    """One tool-like step in the finance agent workflow."""

    tool_name: str
    purpose: str
    input_summary: str
    output_summary: str
    evidence_source_ids: list[str]
    confidence_signal: str
    requires_human_review: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class HumanReviewGate:
    """Human-in-the-loop gate emitted for risky or low-confidence actions."""

    required: bool
    reason_codes: list[str]
    reviewer_prompt: str
    blocking: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_agent_tool_trace(
    *,
    extraction: InvoiceExtraction,
    route: WorkflowRoute,
    context: GroundedPolicyContext,
    assessment_payload: dict[str, Any],
    decision: APDecision | ARDecision,
) -> list[AgentToolTrace]:
    """Translate the deterministic workflow into auditable agent tool calls."""

    evidence_ids = [item.get("source_id", "") for item in context.evidence_payloads if item.get("source_id")]
    traces = [
        AgentToolTrace(
            tool_name="extract_invoice_fields",
            purpose="Convert document text into the strict invoice/email schema.",
            input_summary=f"document_type={extraction.document_type}",
            output_summary=_summarize_extraction(extraction),
            evidence_source_ids=[],
            confidence_signal=_confidence_label(_decision_confidence(decision)),
            requires_human_review=bool(extraction.missing_fields),
        ),
        AgentToolTrace(
            tool_name="route_ap_or_ar",
            purpose="Choose the finance workflow path before policy reasoning.",
            input_summary=f"document_type={extraction.document_type}, invoice={extraction.invoice_number or 'unknown'}",
            output_summary=f"workflow={_enumish(route.workflow_type)}; reason={route.reason}",
            evidence_source_ids=[],
            confidence_signal="deterministic_rule",
        ),
        AgentToolTrace(
            tool_name="search_finance_policy",
            purpose="Retrieve citeable approval, vendor, reminder, or escalation policy.",
            input_summary=context.query_text,
            output_summary=f"{len(context.retrieval_hits)} chunks retrieved",
            evidence_source_ids=evidence_ids,
            confidence_signal="grounded" if evidence_ids else "ungrounded",
            requires_human_review=not evidence_ids,
        ),
    ]

    if _enumish(route.workflow_type) == "accounts_payable":
        traces.extend(_build_ap_traces(extraction, assessment_payload, decision, evidence_ids))
    else:
        traces.extend(_build_ar_traces(assessment_payload, decision, evidence_ids))

    return traces


def build_human_review_gate(
    *,
    extraction: InvoiceExtraction,
    route: WorkflowRoute,
    context: GroundedPolicyContext,
    assessment_payload: dict[str, Any],
    decision: APDecision | ARDecision,
) -> HumanReviewGate:
    """Decide whether a finance reviewer must approve the generated action."""

    reason_codes: list[str] = []
    confidence = _decision_confidence(decision)
    workflow_type = _enumish(route.workflow_type)

    if confidence < 0.75:
        reason_codes.append("low_confidence")
    if extraction.missing_fields:
        reason_codes.append("missing_extracted_fields")
    if not context.evidence_payloads:
        reason_codes.append("missing_policy_evidence")

    if workflow_type == "accounts_payable":
        recommendation = _enumish(getattr(decision, "recommendation", ""))
        if recommendation in {
            ApprovalRecommendation.REVIEW.value,
            ApprovalRecommendation.REJECT.value,
            ApprovalRecommendation.MISSING_INFO.value,
        }:
            reason_codes.append(f"ap_{recommendation}")
        reason_codes.extend(assessment_payload.get("reason_codes", []))
    else:
        escalation_level = _enumish(getattr(decision, "escalation_level", ""))
        if escalation_level in {EscalationLevel.MEDIUM.value, EscalationLevel.HIGH.value}:
            reason_codes.append(f"ar_escalation_{escalation_level}")
        reason_codes.extend(assessment_payload.get("trigger_codes", []))

    cleaned_reasons = _dedupe(reason_codes)
    required = bool(cleaned_reasons)
    return HumanReviewGate(
        required=required,
        reason_codes=cleaned_reasons,
        reviewer_prompt=_build_reviewer_prompt(workflow_type, cleaned_reasons),
        blocking=_is_blocking_review(workflow_type, decision, cleaned_reasons),
    )


def _build_ap_traces(
    extraction: InvoiceExtraction,
    assessment_payload: dict[str, Any],
    decision: APDecision | ARDecision,
    evidence_ids: list[str],
) -> list[AgentToolTrace]:
    anomalies = assessment_payload.get("anomalies", [])
    return [
        AgentToolTrace(
            tool_name="check_duplicate_invoice",
            purpose="Identify duplicate or resubmitted invoices before payment.",
            input_summary=f"invoice={extraction.invoice_number or 'unknown'}",
            output_summary="duplicate_invoice flagged"
            if any(item.get("code") == "duplicate_invoice" for item in anomalies)
            else "no duplicate signal found",
            evidence_source_ids=evidence_ids,
            confidence_signal=_confidence_label(_decision_confidence(decision)),
            requires_human_review=any(item.get("code") == "duplicate_invoice" for item in anomalies),
        ),
        AgentToolTrace(
            tool_name="validate_invoice_math",
            purpose="Compare invoice total against extracted line-item totals.",
            input_summary=f"amount={extraction.amount}, line_items={len(extraction.line_items)}",
            output_summary="amount_mismatch flagged"
            if any(item.get("code") == "amount_mismatch" for item in anomalies)
            else "line-item math accepted or not applicable",
            evidence_source_ids=[],
            confidence_signal="schema_checked",
            requires_human_review=any(item.get("code") == "amount_mismatch" for item in anomalies),
        ),
        AgentToolTrace(
            tool_name="create_audit_summary",
            purpose="Return the final AP action with review rationale and evidence.",
            input_summary=f"reason_codes={', '.join(assessment_payload.get('reason_codes', [])) or 'none'}",
            output_summary=f"recommendation={_enumish(getattr(decision, 'recommendation', 'unknown'))}",
            evidence_source_ids=evidence_ids,
            confidence_signal=_confidence_label(_decision_confidence(decision)),
            requires_human_review=_enumish(getattr(decision, "recommendation", ""))
            != ApprovalRecommendation.APPROVE.value,
        ),
    ]


def _build_ar_traces(
    assessment_payload: dict[str, Any],
    decision: APDecision | ARDecision,
    evidence_ids: list[str],
) -> list[AgentToolTrace]:
    trigger_codes = assessment_payload.get("trigger_codes", [])
    return [
        AgentToolTrace(
            tool_name="assess_ar_escalation",
            purpose="Resolve overdue severity and payment-claim handling.",
            input_summary=f"triggers={', '.join(trigger_codes) or 'none'}",
            output_summary=f"escalation={_enumish(getattr(decision, 'escalation_level', 'unknown'))}",
            evidence_source_ids=evidence_ids,
            confidence_signal=_confidence_label(_decision_confidence(decision)),
            requires_human_review=_enumish(getattr(decision, "escalation_level", ""))
            in {EscalationLevel.MEDIUM.value, EscalationLevel.HIGH.value},
        ),
        AgentToolTrace(
            tool_name="draft_followup_email",
            purpose="Generate a grounded receivables follow-up draft.",
            input_summary=f"evidence={', '.join(evidence_ids) or 'none'}",
            output_summary=f"subject={getattr(decision, 'followup_subject', '')}",
            evidence_source_ids=evidence_ids,
            confidence_signal=_confidence_label(_decision_confidence(decision)),
            requires_human_review="payment_claim_without_proof" in trigger_codes,
        ),
    ]


def _summarize_extraction(extraction: InvoiceExtraction) -> str:
    entity = extraction.vendor_name or extraction.customer_name or "unknown_party"
    missing = ", ".join(extraction.missing_fields) if extraction.missing_fields else "none"
    return (
        f"entity={entity}; invoice={extraction.invoice_number or 'unknown'}; "
        f"amount={extraction.amount}; missing={missing}"
    )


def _build_reviewer_prompt(workflow_type: str, reason_codes: list[str]) -> str:
    if not reason_codes:
        return "No human review is required for this workflow result."
    if workflow_type == "accounts_payable":
        return "Review the extracted invoice fields, cited policy, and AP anomaly list before payment action."
    return "Review the cited reminder policy and follow-up draft before customer-facing outreach."


def _is_blocking_review(
    workflow_type: str,
    decision: APDecision | ARDecision,
    reason_codes: list[str],
) -> bool:
    if "missing_policy_evidence" in reason_codes or "low_confidence" in reason_codes:
        return True
    if workflow_type == "accounts_payable":
        return _enumish(getattr(decision, "recommendation", "")) in {
            ApprovalRecommendation.REJECT.value,
            ApprovalRecommendation.MISSING_INFO.value,
        }
    return _enumish(getattr(decision, "escalation_level", "")) == EscalationLevel.HIGH.value


def _decision_confidence(decision: APDecision | ARDecision) -> float:
    return float(getattr(decision, "confidence", 0.0) or 0.0)


def _confidence_label(confidence: float) -> str:
    if confidence >= 0.9:
        return "high_confidence"
    if confidence >= 0.75:
        return "medium_confidence"
    return "low_confidence"


def _enumish(raw_value: Any) -> str:
    if hasattr(raw_value, "value"):
        return str(raw_value.value)
    return str(raw_value)


def _dedupe(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value).strip()
        if item and item not in seen:
            ordered.append(item)
            seen.add(item)
    return ordered
