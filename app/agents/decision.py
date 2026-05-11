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
    evidence = _select_evidence(context)

    return APDecision(
        recommendation=recommendation,
        reviewer_summary=reviewer_summary,
        evidence=evidence,
        anomalies=anomalies,
        confidence=confidence,
    )


def _resolve_ap_recommendation(anomalies: list[AnomalyFlag]) -> ApprovalRecommendation:
    codes = {anomaly.code for anomaly in anomalies}
    if "invalid_invoice" in codes:
        return ApprovalRecommendation.REJECT
    if "missing_required_fields" in codes or "missing_po" in codes:
        return ApprovalRecommendation.MISSING_INFO
    if "duplicate_invoice" in codes or "terms_mismatch" in codes or "approval_threshold" in codes:
        return ApprovalRecommendation.REVIEW
    return ApprovalRecommendation.APPROVE


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


def _select_evidence(context: GroundedPolicyContext) -> list[dict[str, str]]:
    if context.evidence_payloads:
        return context.evidence_payloads[:4]
    return [
        {
            "source_id": "context-summary",
            "source_title": "Grounded Policy Context",
            "excerpt": context.summary,
            "relevance_reason": "Fallback context summary when no KB evidence was returned.",
        }
    ]
