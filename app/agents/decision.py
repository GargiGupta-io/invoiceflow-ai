"""Decision logic for accounts-payable workflow cases."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol

from ..schemas.decision import APDecision, AnomalyFlag, ApprovalRecommendation, EscalationLevel
from .research import GroundedPolicyContext

TERMS_RE = re.compile(r"Standard payment terms:\s*(?P<terms>.+)", re.IGNORECASE)
PO_RE = re.compile(r"PO required above:\s*(?P<value>.+)", re.IGNORECASE)
SERVICES_EXEMPT_RE = re.compile(r"Services exempt:\s*(?P<value>yes|no)", re.IGNORECASE)


class APExtractionLike(Protocol):
    """Small protocol for the extraction fields used by AP decisioning."""

    vendor_name: str | None
    invoice_number: str | None
    po_number: str | None
    amount: float | None
    currency: Any
    due_date: Any
    payment_terms: str | None
    source_text_excerpt: str
    missing_fields: list[str]
    extraction_warnings: list[str]


@dataclass(slots=True)
class VendorPolicy:
    """Vendor-specific policy hints extracted from grounded evidence."""

    standard_terms: str | None = None
    po_required_above: float | None = None
    services_exempt: bool = False


def decide_accounts_payable(
    extraction: APExtractionLike,
    context: GroundedPolicyContext,
) -> APDecision:
    """Produce the AP recommendation, anomalies, and reviewer summary."""

    anomalies: list[AnomalyFlag] = []
    vendor_policy = _extract_vendor_policy(context)

    required_missing = [
        field_name
        for field_name in extraction.missing_fields
        if field_name in {"vendor_name", "invoice_number", "amount", "currency", "due_date"}
    ]
    if required_missing:
        anomalies.append(
            _build_anomaly(
                code="missing_required_fields",
                message=f"Missing required invoice fields: {', '.join(required_missing)}.",
                severity=EscalationLevel.MEDIUM,
            )
        )

    if _requires_purchase_order(extraction.amount, vendor_policy) and not extraction.po_number:
        anomalies.append(
            _build_anomaly(
                code="missing_po",
                message="Invoice requires a purchase order before AP can complete review.",
                severity=EscalationLevel.MEDIUM,
            )
        )

    if _is_duplicate_case(extraction):
        anomalies.append(
            _build_anomaly(
                code="duplicate_invoice",
                message="Invoice appears to be a duplicate or resubmission and needs manual review.",
                severity=EscalationLevel.MEDIUM,
            )
        )

    if _payment_terms_mismatch(extraction.payment_terms, vendor_policy.standard_terms):
        anomalies.append(
            _build_anomaly(
                code="terms_mismatch",
                message="Invoice payment terms do not match the vendor's agreed master terms.",
                severity=EscalationLevel.MEDIUM,
            )
        )

    if _is_invalid_invoice(extraction):
        anomalies.append(
            _build_anomaly(
                code="invalid_invoice",
                message="Invoice appears void, cancelled, or otherwise invalid for payment processing.",
                severity=EscalationLevel.HIGH,
            )
        )

    threshold_anomaly = _threshold_anomaly(extraction.amount)
    if threshold_anomaly is not None:
        anomalies.append(threshold_anomaly)

    recommendation = _resolve_ap_recommendation(anomalies)
    reviewer_summary = _build_reviewer_summary(recommendation, anomalies, extraction)
    confidence = _estimate_confidence(recommendation, anomalies, context)
    evidence = _select_evidence(context)

    return APDecision(
        recommendation=recommendation,
        reviewer_summary=reviewer_summary,
        evidence=evidence,
        anomalies=anomalies,
        confidence=confidence,
    )


def _extract_vendor_policy(context: GroundedPolicyContext) -> VendorPolicy:
    policy = VendorPolicy()
    for hit in context.retrieval_hits:
        if not hit.source_id.startswith("VENDOR-"):
            continue

        terms_match = TERMS_RE.search(hit.excerpt)
        if terms_match:
            policy.standard_terms = terms_match.group("terms").strip()

        po_match = PO_RE.search(hit.excerpt)
        if po_match:
            raw_value = po_match.group("value").strip().lower()
            if raw_value == "none":
                policy.po_required_above = None
            else:
                policy.po_required_above = _parse_float(raw_value)

        services_match = SERVICES_EXEMPT_RE.search(hit.excerpt)
        if services_match:
            policy.services_exempt = services_match.group("value").strip().lower() == "yes"

    return policy


def _requires_purchase_order(amount: float | None, vendor_policy: VendorPolicy) -> bool:
    if vendor_policy.services_exempt:
        return False
    threshold = vendor_policy.po_required_above
    if threshold is None:
        threshold = 3000.0
    if amount is None:
        return True
    return amount > threshold


def _is_duplicate_case(extraction: APExtractionLike) -> bool:
    text = extraction.source_text_excerpt.lower()
    warning_text = " ".join(extraction.extraction_warnings).lower()
    return any(
        marker in text or marker in warning_text
        for marker in ("duplicate", "resubmitted", "resubmission")
    )


def _payment_terms_mismatch(
    detected_terms: str | None,
    expected_terms: str | None,
) -> bool:
    if not detected_terms or not expected_terms:
        return False
    return detected_terms.strip().lower() != expected_terms.strip().lower()


def _threshold_anomaly(amount: float | None) -> AnomalyFlag | None:
    if amount is None:
        return None
    if amount > 5000.0:
        return _build_anomaly(
            code="approval_threshold",
            message="Invoice exceeds the auto-approval threshold and needs manual approval review.",
            severity=EscalationLevel.LOW,
        )
    return None


def _is_invalid_invoice(extraction: APExtractionLike) -> bool:
    text = extraction.source_text_excerpt.lower()
    return any(marker in text for marker in ("void invoice", "invoice void", "cancelled", "canceled"))


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
) -> float:
    base = 0.92
    base -= min(len(anomalies) * 0.06, 0.18)
    if len(context.retrieval_hits) < 2:
        base -= 0.08
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


def _build_anomaly(code: str, message: str, severity: EscalationLevel) -> AnomalyFlag:
    return AnomalyFlag(code=code, message=message, severity=severity)


def _parse_float(raw_value: str) -> float | None:
    cleaned = raw_value.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None
