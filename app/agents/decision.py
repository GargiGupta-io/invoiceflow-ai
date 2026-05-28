"""Decision logic for accounts-payable workflow cases."""

from __future__ import annotations

from typing import Any, Protocol

from ..schemas.decision import APDecision, AnomalyFlag, ApprovalRecommendation, EscalationLevel
from .policy import APWorkflowAssessment, assess_accounts_payable
from .research import GroundedPolicyContext


class APExtractionLike(Protocol):
    """Small protocol for the extraction fields used by AP decisioning."""

    vendor_name: str | None
    invoice_number: str | None
    po_number: str | None
    amount: float | None
    currency: Any
    due_date: Any
    payment_terms: str | None
    line_items: list[Any]
    source_text_excerpt: str
    missing_fields: list[str]
    extraction_warnings: list[str]


def decide_accounts_payable(
    extraction: APExtractionLike,
    context: GroundedPolicyContext,
) -> APDecision:
    """Produce the AP recommendation, anomalies, and reviewer summary."""

    assessment = assess_accounts_payable(extraction, context)
    anomalies = assessment.anomalies
    recommendation = _resolve_ap_recommendation(anomalies)
    reviewer_summary = _build_reviewer_summary(recommendation, anomalies, extraction)
    confidence = _estimate_confidence(recommendation, anomalies, context, assessment)
    evidence = _select_evidence(context, extraction, assessment, recommendation)
    missing_fields = _build_missing_field_output(extraction)

    return APDecision(
        recommendation=recommendation,
        missing_fields=missing_fields,
        reviewer_summary=reviewer_summary,
        evidence=evidence,
        policy_evidence=evidence,
        anomalies=anomalies,
        human_review_required=_requires_ap_human_review(recommendation, anomalies, confidence),
        confidence=confidence,
    )


def _resolve_ap_recommendation(anomalies: list[AnomalyFlag]) -> ApprovalRecommendation:
    codes = {anomaly.code for anomaly in anomalies}
    if "invalid_invoice" in codes:
        return ApprovalRecommendation.REJECT
    if any(code.startswith("missing_") for code in codes):
        return ApprovalRecommendation.MISSING_INFO
    if "duplicate_invoice" in codes or "terms_mismatch" in codes or "approval_threshold" in codes:
        return ApprovalRecommendation.REVIEW
    return ApprovalRecommendation.APPROVE


def _build_missing_field_output(extraction: APExtractionLike) -> list[str]:
    required_fields = ["vendor_name", "invoice_number", "due_date"]
    missing_fields = [
        field_name
        for field_name in required_fields
        if not getattr(extraction, field_name, None)
    ]
    missing_fields.extend(extraction.missing_fields)
    if not extraction.po_number:
        missing_fields.append("po_number")
    return _dedupe_strings(missing_fields)


def _requires_ap_human_review(
    recommendation: ApprovalRecommendation,
    anomalies: list[AnomalyFlag],
    confidence: float,
) -> bool:
    if confidence < 0.75:
        return True
    if recommendation != ApprovalRecommendation.APPROVE:
        return True
    review_severities = {EscalationLevel.MEDIUM.value, EscalationLevel.HIGH.value}
    return any(_enum_value(anomaly.severity) in review_severities for anomaly in anomalies)


def _build_reviewer_summary(
    recommendation: ApprovalRecommendation,
    anomalies: list[AnomalyFlag],
    extraction: APExtractionLike,
) -> str:
    invoice_label = extraction.invoice_number or "the submitted invoice"

    if recommendation == ApprovalRecommendation.APPROVE:
        return (
            f"{invoice_label} cleared the AP checks with no blocking policy conflicts. "
            "Proceed with normal payment processing."
        )

    top_anomaly = anomalies[0] if anomalies else None
    if recommendation == ApprovalRecommendation.MISSING_INFO and top_anomaly is not None:
        return (
            f"{invoice_label} is missing information needed for AP review. "
            f"Primary issue: {top_anomaly.message} Request the missing details before continuing."
        )

    if recommendation == ApprovalRecommendation.REVIEW and top_anomaly is not None:
        return (
            f"{invoice_label} needs manual AP review before payment. "
            f"Primary issue: {top_anomaly.message}"
        )

    if recommendation == ApprovalRecommendation.REJECT and top_anomaly is not None:
        return (
            f"{invoice_label} should not move forward in AP. "
            f"Primary issue: {top_anomaly.message}"
        )

    return f"{invoice_label} requires additional AP attention before payment can continue."


def _estimate_confidence(
    recommendation: ApprovalRecommendation,
    anomalies: list[AnomalyFlag],
    context: GroundedPolicyContext,
    assessment: APWorkflowAssessment,
) -> float:
    base = 0.92
    base -= min(len(anomalies) * 0.06, 0.18)
    if len(context.retrieval_hits) < 2:
        base -= 0.08
    base -= min(len(assessment.reason_codes) * 0.01, 0.04)
    if recommendation == ApprovalRecommendation.APPROVE:
        base += 0.02
    return max(0.45, min(round(base, 2), 0.99))


def _select_evidence(
    context: GroundedPolicyContext,
    extraction: APExtractionLike,
    assessment: APWorkflowAssessment,
    recommendation: ApprovalRecommendation,
) -> list[dict[str, str]]:
    if context.evidence_payloads:
        required_source_ids = _required_ap_source_ids(extraction, assessment, recommendation)
        return _select_ordered_evidence(context.evidence_payloads, required_source_ids, limit=4)
    return [
        {
            "source_id": "context-summary",
            "source_title": "Grounded Policy Context",
            "excerpt": context.summary,
            "relevance_reason": "Fallback context summary when no KB evidence was returned.",
        }
    ]


def _required_ap_source_ids(
    extraction: APExtractionLike,
    assessment: APWorkflowAssessment,
    recommendation: ApprovalRecommendation,
) -> list[str]:
    source_ids: list[str] = []
    anomaly_codes = {anomaly.code for anomaly in assessment.anomalies}

    if recommendation == ApprovalRecommendation.APPROVE or "approval_threshold" in anomaly_codes:
        source_ids.append("AP-APPROVAL-001")
    if "missing_po" in anomaly_codes:
        source_ids.append("AP-APPROVAL-002")
    if "duplicate_invoice" in anomaly_codes:
        source_ids.append("AP-APPROVAL-003")
    source_ids.append("AP-POLICY-003")

    vendor_source_id = _vendor_source_id(extraction.vendor_name)
    if vendor_source_id:
        source_ids.append(vendor_source_id)
    return source_ids


def _vendor_source_id(vendor_name: str | None) -> str | None:
    normalized = (vendor_name or "").strip().lower()
    vendor_ids = {
        "northstar office supplies": "VENDOR-001",
        "bluewave logistics": "VENDOR-002",
        "lumina creative studio": "VENDOR-003",
        "quartz cloud systems": "VENDOR-004",
    }
    return vendor_ids.get(normalized)


def _select_ordered_evidence(
    evidence_payloads: list[dict[str, str]],
    required_source_ids: list[str],
    *,
    limit: int,
) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    selected_ids: set[str] = set()
    evidence_by_id = {item.get("source_id"): item for item in evidence_payloads}

    for source_id in required_source_ids:
        item = evidence_by_id.get(source_id)
        if item is None or source_id in selected_ids:
            continue
        selected.append(item)
        selected_ids.add(source_id)

    for item in evidence_payloads:
        source_id = item.get("source_id", "")
        if source_id in selected_ids:
            continue
        selected.append(item)
        selected_ids.add(source_id)
        if len(selected) >= limit:
            break

    return selected[:limit]


def _dedupe_strings(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value).strip()
        if item and item not in seen:
            ordered.append(item)
            seen.add(item)
    return ordered


def _enum_value(raw_value: Any) -> str:
    if hasattr(raw_value, "value"):
        return str(raw_value.value)
    return str(raw_value)
