"""Shared workflow policy and anomaly assessment helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

from ..schemas.decision import AnomalyFlag, EscalationLevel
from ..schemas.invoice import DocumentType
from .research import GroundedPolicyContext

TERMS_RE = re.compile(r"Standard payment terms:\s*(?P<terms>.+)", re.IGNORECASE)
PO_RE = re.compile(r"PO required above:\s*(?P<value>.+)", re.IGNORECASE)
SERVICES_EXEMPT_RE = re.compile(r"Services exempt:\s*(?P<value>yes|no)", re.IGNORECASE)
TONE_RE = re.compile(r"Preferred reminder tone:\s*(?P<value>.+)", re.IGNORECASE)
OVERDUE_DAYS_RE = re.compile(r"Overdue Days:\s*(?P<value>\d+)", re.IGNORECASE)
PRIOR_REMINDERS_RE = re.compile(r"Prior Reminders Sent:\s*(?P<value>\d+)", re.IGNORECASE)


class APExtractionLike(Protocol):
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
    line_items: list[Any]


class ARExtractionLike(Protocol):
    document_type: Any
    customer_name: str | None
    invoice_number: str | None
    amount: float | None
    currency: Any
    due_date: date | str | None
    source_text_excerpt: str
    missing_fields: list[str]
    extraction_warnings: list[str]


@dataclass(slots=True)
class VendorPolicy:
    standard_terms: str | None = None
    po_required_above: float | None = None
    services_exempt: bool = False


@dataclass(slots=True)
class CustomerPolicy:
    preferred_tone: str | None = None


@dataclass(slots=True)
class APWorkflowAssessment:
    vendor_policy: VendorPolicy
    anomalies: list[AnomalyFlag]
    reason_codes: list[str]


@dataclass(slots=True)
class ARWorkflowAssessment:
    customer_policy: CustomerPolicy
    escalation_level: EscalationLevel
    payment_claim: bool
    overdue_days: int | None
    prior_reminders: int | None
    trigger_codes: list[str]


def assess_accounts_payable(
    extraction: APExtractionLike,
    context: GroundedPolicyContext,
) -> APWorkflowAssessment:
    """Build AP anomalies and workflow reasons from extraction plus grounded policy."""

    vendor_policy = extract_vendor_policy(context)
    anomalies: list[AnomalyFlag] = []
    reason_codes: list[str] = []

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
        reason_codes.append("required_fields_missing")

    if requires_purchase_order(extraction.amount, vendor_policy) and not extraction.po_number:
        anomalies.append(
            _build_anomaly(
                code="missing_po",
                message="Invoice requires a purchase order before AP can complete review.",
                severity=EscalationLevel.MEDIUM,
            )
        )
        reason_codes.append("po_required_missing")

    if is_duplicate_case(extraction):
        anomalies.append(
            _build_anomaly(
                code="duplicate_invoice",
                message="Invoice appears to be a duplicate or resubmission and needs manual review.",
                severity=EscalationLevel.MEDIUM,
            )
        )
        reason_codes.append("duplicate_invoice_detected")

    if payment_terms_mismatch(extraction.payment_terms, vendor_policy.standard_terms):
        anomalies.append(
            _build_anomaly(
                code="terms_mismatch",
                message="Invoice payment terms do not match the vendor's agreed master terms.",
                severity=EscalationLevel.MEDIUM,
            )
        )
        reason_codes.append("vendor_terms_mismatch")

    if is_invalid_invoice(extraction):
        anomalies.append(
            _build_anomaly(
                code="invalid_invoice",
                message="Invoice appears void, cancelled, or otherwise invalid for payment processing.",
                severity=EscalationLevel.HIGH,
            )
        )
        reason_codes.append("invalid_invoice_state")

    amount_mismatch = amount_mismatch_anomaly(extraction)
    if amount_mismatch is not None:
        anomalies.append(amount_mismatch)
        reason_codes.append("line_item_total_mismatch")

    threshold_anomaly = approval_threshold_anomaly(extraction.amount)
    if threshold_anomaly is not None:
        anomalies.append(threshold_anomaly)
        reason_codes.append("manual_threshold_review")

    return APWorkflowAssessment(
        vendor_policy=vendor_policy,
        anomalies=anomalies,
        reason_codes=_dedupe_strings(reason_codes),
    )


def assess_accounts_receivable(
    extraction: ARExtractionLike,
    context: GroundedPolicyContext,
) -> ARWorkflowAssessment:
    """Build AR escalation triggers and customer-policy hints."""

    customer_policy = extract_customer_policy(context)
    overdue_days = parse_int_from_excerpt(OVERDUE_DAYS_RE, extraction.source_text_excerpt)
    prior_reminders = parse_int_from_excerpt(PRIOR_REMINDERS_RE, extraction.source_text_excerpt)
    payment_claim = is_payment_claim_case(extraction)
    escalation_level = resolve_escalation_level(
        overdue_days=overdue_days,
        prior_reminders=prior_reminders,
        payment_claim=payment_claim,
    )

    trigger_codes: list[str] = []
    if payment_claim:
        trigger_codes.append("payment_claim_without_proof")
    if overdue_days is not None:
        if overdue_days >= 45:
            trigger_codes.append("high_overdue_days")
        elif overdue_days >= 22:
            trigger_codes.append("medium_overdue_days")
        elif overdue_days >= 8:
            trigger_codes.append("low_overdue_days")
        else:
            trigger_codes.append("early_overdue_days")
    if prior_reminders is not None:
        if prior_reminders >= 3:
            trigger_codes.append("repeated_reminders_high")
        elif prior_reminders >= 2:
            trigger_codes.append("repeated_reminders_medium")
        elif prior_reminders >= 1:
            trigger_codes.append("repeated_reminders_low")
    if "due_date" in extraction.missing_fields:
        trigger_codes.append("missing_due_date")
    if "invoice_number" in extraction.missing_fields:
        trigger_codes.append("missing_invoice_number")

    trigger_codes.append(f"escalation_{escalation_level.value}")

    return ARWorkflowAssessment(
        customer_policy=customer_policy,
        escalation_level=escalation_level,
        payment_claim=payment_claim,
        overdue_days=overdue_days,
        prior_reminders=prior_reminders,
        trigger_codes=_dedupe_strings(trigger_codes),
    )


def extract_vendor_policy(context: GroundedPolicyContext) -> VendorPolicy:
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


def extract_customer_policy(context: GroundedPolicyContext) -> CustomerPolicy:
    policy = CustomerPolicy()
    for hit in context.retrieval_hits:
        if not hit.source_id.startswith("CUSTOMER-"):
            continue
        tone_match = TONE_RE.search(hit.excerpt)
        if tone_match:
            policy.preferred_tone = tone_match.group("value").strip()
            break
    return policy


def requires_purchase_order(amount: float | None, vendor_policy: VendorPolicy) -> bool:
    if vendor_policy.services_exempt:
        return False
    threshold = vendor_policy.po_required_above
    if threshold is None:
        threshold = 3000.0
    if amount is None:
        return True
    return amount > threshold


def is_duplicate_case(extraction: APExtractionLike) -> bool:
    text = extraction.source_text_excerpt.lower()
    warning_text = " ".join(extraction.extraction_warnings).lower()
    return any(
        marker in text or marker in warning_text
        for marker in ("duplicate", "resubmitted", "resubmission")
    )


def payment_terms_mismatch(
    detected_terms: str | None,
    expected_terms: str | None,
) -> bool:
    if not detected_terms or not expected_terms:
        return False
    return detected_terms.strip().lower() != expected_terms.strip().lower()


def is_invalid_invoice(extraction: APExtractionLike) -> bool:
    text = extraction.source_text_excerpt.lower()
    return any(marker in text for marker in ("void invoice", "invoice void", "cancelled", "canceled"))


def approval_threshold_anomaly(amount: float | None) -> AnomalyFlag | None:
    if amount is None:
        return None
    if amount > 5000.0:
        return _build_anomaly(
            code="approval_threshold",
            message="Invoice exceeds the auto-approval threshold and needs manual approval review.",
            severity=EscalationLevel.LOW,
        )
    return None


def amount_mismatch_anomaly(extraction: APExtractionLike) -> AnomalyFlag | None:
    amount = extraction.amount
    if amount is None or not extraction.line_items:
        return None

    computed_total = 0.0
    has_item_total = False
    for item in extraction.line_items:
        line_total = getattr(item, "line_total", None)
        if line_total is None:
            continue
        has_item_total = True
        computed_total += float(line_total)

    if not has_item_total:
        return None

    if abs(computed_total - amount) > 0.01:
        return _build_anomaly(
            code="amount_mismatch",
            message=(
                "Invoice total does not match the summed line-item amount and needs manual verification."
            ),
            severity=EscalationLevel.MEDIUM,
        )
    return None


def resolve_escalation_level(
    *,
    overdue_days: int | None,
    prior_reminders: int | None,
    payment_claim: bool,
) -> EscalationLevel:
    if payment_claim:
        return EscalationLevel.LOW

    reminders = prior_reminders or 0
    days = overdue_days or 0

    if days > 45 or reminders >= 3:
        return EscalationLevel.HIGH
    if days >= 22 or reminders >= 2:
        return EscalationLevel.MEDIUM
    if days >= 8 or reminders >= 1:
        return EscalationLevel.LOW
    return EscalationLevel.NONE


def parse_int_from_excerpt(pattern: re.Pattern[str], excerpt: str) -> int | None:
    match = pattern.search(excerpt)
    if match is None:
        return None
    try:
        return int(match.group("value"))
    except ValueError:
        return None


def is_payment_claim_case(extraction: ARExtractionLike) -> bool:
    document_type = document_type_value(extraction.document_type)
    if document_type == DocumentType.PAYMENT_CONFIRMATION.value:
        return True
    text = extraction.source_text_excerpt.lower()
    return any(
        marker in text
        for marker in (
            "payment has already been initiated",
            "payment has already been made",
            "transaction reference",
            "remittance proof",
        )
    )


def document_type_value(raw_value: Any) -> str:
    if raw_value is None:
        return ""
    if hasattr(raw_value, "value"):
        return str(raw_value.value)
    return str(raw_value)


def _build_anomaly(code: str, message: str, severity: EscalationLevel) -> AnomalyFlag:
    return AnomalyFlag(code=code, message=message, severity=severity)


def _parse_float(raw_value: str) -> float | None:
    cleaned = raw_value.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        item = value.strip()
        if item and item not in seen:
            ordered.append(item)
            seen.add(item)
    return ordered
