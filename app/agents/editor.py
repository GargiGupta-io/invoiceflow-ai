"""Draft follow-up actions for accounts-receivable workflow cases."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

from ..schemas.decision import ARDecision, EscalationLevel
from ..schemas.invoice import DocumentType
from .research import GroundedPolicyContext

OVERDUE_DAYS_RE = re.compile(r"Overdue Days:\s*(?P<value>\d+)", re.IGNORECASE)
PRIOR_REMINDERS_RE = re.compile(r"Prior Reminders Sent:\s*(?P<value>\d+)", re.IGNORECASE)
TONE_RE = re.compile(r"Preferred reminder tone:\s*(?P<value>.+)", re.IGNORECASE)


class ARExtractionLike(Protocol):
    """Small protocol for the extraction fields used by AR drafting."""

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
class CustomerPolicy:
    """Customer-specific tone or escalation hints from grounded evidence."""

    preferred_tone: str | None = None


def draft_accounts_receivable(
    extraction: ARExtractionLike,
    context: GroundedPolicyContext,
) -> ARDecision:
    """Produce the AR escalation level, subject, and follow-up draft."""

    customer_policy = _extract_customer_policy(context)
    overdue_days = _parse_int_from_excerpt(OVERDUE_DAYS_RE, extraction.source_text_excerpt)
    prior_reminders = _parse_int_from_excerpt(PRIOR_REMINDERS_RE, extraction.source_text_excerpt)
    payment_claim = _is_payment_claim_case(extraction)
    escalation_level = _resolve_escalation_level(
        extraction=extraction,
        overdue_days=overdue_days,
        prior_reminders=prior_reminders,
        payment_claim=payment_claim,
    )
    subject = _build_subject(extraction, escalation_level, payment_claim)
    draft = _build_followup_draft(
        extraction=extraction,
        escalation_level=escalation_level,
        payment_claim=payment_claim,
        prior_reminders=prior_reminders,
        customer_policy=customer_policy,
    )
    confidence = _estimate_confidence(escalation_level, payment_claim, context)
    evidence = _select_evidence(context)

    return ARDecision(
        escalation_level=escalation_level,
        followup_subject=subject,
        followup_draft=draft,
        evidence=evidence,
        confidence=confidence,
    )


def _extract_customer_policy(context: GroundedPolicyContext) -> CustomerPolicy:
    policy = CustomerPolicy()
    for hit in context.retrieval_hits:
        if not hit.source_id.startswith("CUSTOMER-"):
            continue
        tone_match = TONE_RE.search(hit.excerpt)
        if tone_match:
            policy.preferred_tone = tone_match.group("value").strip()
            break
    return policy


def _resolve_escalation_level(
    *,
    extraction: ARExtractionLike,
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


def _build_subject(
    extraction: ARExtractionLike,
    escalation_level: EscalationLevel,
    payment_claim: bool,
) -> str:
    invoice_number = extraction.invoice_number or "invoice"
    if payment_claim:
        return f"Follow-up on payment confirmation for {invoice_number}"
    if escalation_level == EscalationLevel.NONE:
        return f"Friendly reminder: invoice {invoice_number} was due on {_due_date_text(extraction.due_date)}"
    if escalation_level == EscalationLevel.LOW:
        return f"Second reminder: invoice {invoice_number} remains unpaid"
    return f"Action requested: overdue invoice {invoice_number}"


def _build_followup_draft(
    *,
    extraction: ARExtractionLike,
    escalation_level: EscalationLevel,
    payment_claim: bool,
    prior_reminders: int | None,
    customer_policy: CustomerPolicy,
) -> str:
    customer_name = extraction.customer_name or "team"
    invoice_number = extraction.invoice_number or "the invoice"
    amount_text = _amount_text(extraction.amount, extraction.currency)
    due_date_text = _due_date_text(extraction.due_date)
    tone_line = _tone_sentence(customer_policy.preferred_tone)

    if payment_claim:
        return (
            f"Hello {customer_name},\n\n"
            f"Thanks for the update on invoice {invoice_number} for {amount_text}. "
            f"We have not yet been able to match the payment in our records. "
            f"Could you please share the transfer date, transaction reference, and remittance advice "
            "so we can reconcile it on our side?\n\n"
            f"{tone_line}"
        )

    if escalation_level == EscalationLevel.NONE:
        return (
            f"Hello {customer_name},\n\n"
            f"This is a quick reminder that invoice {invoice_number} for {amount_text} was due on {due_date_text}. "
            "If payment has already been initiated, please share the transfer details. "
            "Otherwise, could you let us know the expected payment date?\n\n"
            f"{tone_line}"
        )

    if escalation_level == EscalationLevel.LOW:
        reminder_line = ""
        if (prior_reminders or 0) >= 1:
            reminder_line = "This follows our earlier reminder on the same invoice. "
        return (
            f"Hello {customer_name},\n\n"
            f"Invoice {invoice_number} for {amount_text} remains unpaid after its due date of {due_date_text}. "
            f"{reminder_line}"
            "Please share a firm payment timeline or let us know if there is any issue on your side.\n\n"
            f"{tone_line}"
        )

    if escalation_level == EscalationLevel.MEDIUM:
        return (
            f"Hello {customer_name},\n\n"
            f"Invoice {invoice_number} for {amount_text} remains overdue since {due_date_text}. "
            "We have already followed up and still do not have a confirmed payment date. "
            "Please send immediate confirmation of status or share a payment plan so we can align next steps.\n\n"
            f"{tone_line}"
        )

    return (
        f"Hello {customer_name},\n\n"
        f"Invoice {invoice_number} for {amount_text} is now significantly overdue beyond {due_date_text}. "
        "We need urgent confirmation of payment status or a firm resolution plan today so this can be closed without further escalation.\n\n"
        f"{tone_line}"
    )


def _estimate_confidence(
    escalation_level: EscalationLevel,
    payment_claim: bool,
    context: GroundedPolicyContext,
) -> float:
    base = 0.9
    if payment_claim:
        base += 0.03
    if escalation_level in {EscalationLevel.MEDIUM, EscalationLevel.HIGH}:
        base -= 0.04
    if len(context.retrieval_hits) < 2:
        base -= 0.08
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


def _parse_int_from_excerpt(pattern: re.Pattern[str], excerpt: str) -> int | None:
    match = pattern.search(excerpt)
    if match is None:
        return None
    try:
        return int(match.group("value"))
    except ValueError:
        return None


def _is_payment_claim_case(extraction: ARExtractionLike) -> bool:
    document_type = _document_type_value(extraction.document_type)
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


def _document_type_value(raw_value: Any) -> str:
    if raw_value is None:
        return ""
    if hasattr(raw_value, "value"):
        return str(raw_value.value)
    return str(raw_value)


def _due_date_text(raw_value: date | str | None) -> str:
    if raw_value is None:
        return "the stated due date"
    if isinstance(raw_value, date):
        return raw_value.isoformat()
    return str(raw_value)


def _amount_text(amount: float | None, currency: Any) -> str:
    if amount is None:
        return "the outstanding amount"
    currency_text = " ".join(part for part in (_currency_text(currency), f"{amount:.2f}") if part)
    return currency_text or f"{amount:.2f}"


def _currency_text(raw_value: Any) -> str:
    if raw_value is None:
        return ""
    if hasattr(raw_value, "value"):
        return str(raw_value.value)
    return str(raw_value)


def _tone_sentence(raw_tone: str | None) -> str:
    if not raw_tone:
        return "Please let us know if you need anything else from our side."
    lowered = raw_tone.lower()
    if "collaborative" in lowered:
        return "If there is any blocker on your side, we are happy to work through it together."
    if "direct" in lowered:
        return "A prompt confirmation from your side would help us close this out quickly."
    if "firm" in lowered:
        return "Please treat this as a priority and confirm the payment plan today."
    return "Please let us know if you need anything else from our side."
