"""Draft follow-up actions for accounts-receivable workflow cases."""

from __future__ import annotations

from datetime import date
from typing import Any, Protocol

from ..schemas.decision import ARDecision, EscalationLevel
from .policy import ARWorkflowAssessment, assess_accounts_receivable
from .research import GroundedPolicyContext
from .tts import tts_safe_amount_text, tts_safe_date_text, tts_safe_identifier


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


def draft_accounts_receivable(
    extraction: ARExtractionLike,
    context: GroundedPolicyContext,
) -> ARDecision:
    """Produce the AR escalation level, subject, and follow-up draft."""

    assessment = assess_accounts_receivable(extraction, context)
    escalation_level = assessment.escalation_level
    payment_claim = assessment.payment_claim
    subject = _build_subject(extraction, assessment)
    draft = _build_followup_draft(
        extraction=extraction,
        assessment=assessment,
    )
    subject_tts = _build_subject_tts(extraction, assessment)
    draft_tts = _build_followup_draft_tts(
        extraction=extraction,
        assessment=assessment,
    )
    confidence = _estimate_confidence(context, assessment)
    evidence = _select_evidence(context, extraction, assessment)

    return ARDecision(
        escalation_level=escalation_level,
        followup_subject=subject,
        followup_draft=draft,
        followup_subject_tts=subject_tts,
        followup_draft_tts=draft_tts,
        evidence=evidence,
        confidence=confidence,
    )


def _build_subject(
    extraction: ARExtractionLike,
    assessment: ARWorkflowAssessment,
) -> str:
    invoice_number = extraction.invoice_number or "invoice"
    if assessment.payment_claim:
        return f"Follow-up on payment confirmation for {invoice_number}"
    if assessment.escalation_level == EscalationLevel.NONE:
        return f"Friendly reminder: invoice {invoice_number} was due on {_due_date_text(extraction.due_date)}"
    if assessment.escalation_level == EscalationLevel.LOW:
        return f"Second reminder: invoice {invoice_number} remains unpaid"
    return f"Action requested: overdue invoice {invoice_number}"


def _build_followup_draft(
    *,
    extraction: ARExtractionLike,
    assessment: ARWorkflowAssessment,
) -> str:
    customer_name = extraction.customer_name or "team"
    invoice_number = extraction.invoice_number or "the invoice"
    amount_text = _amount_text(extraction.amount, extraction.currency)
    due_date_text = _due_date_text(extraction.due_date)
    tone_line = _tone_sentence(assessment.customer_policy.preferred_tone)

    if assessment.payment_claim:
        return (
            f"Hello {customer_name},\n\n"
            f"Thanks for the update on invoice {invoice_number} for {amount_text}. "
            f"We have not yet been able to match the payment in our records. "
            f"Could you please share the transfer date, transaction reference, and remittance advice "
            "so we can reconcile it on our side?\n\n"
            f"{tone_line}"
        )

    if assessment.escalation_level == EscalationLevel.NONE:
        return (
            f"Hello {customer_name},\n\n"
            f"This is a quick reminder that invoice {invoice_number} for {amount_text} was due on {due_date_text}. "
            "If payment has already been initiated, please share the transfer details. "
            "Otherwise, could you let us know the expected payment date?\n\n"
            f"{tone_line}"
        )

    if assessment.escalation_level == EscalationLevel.LOW:
        reminder_line = ""
        if (assessment.prior_reminders or 0) >= 1:
            reminder_line = "This follows our earlier reminder on the same invoice. "
        return (
            f"Hello {customer_name},\n\n"
            f"Invoice {invoice_number} for {amount_text} remains unpaid after its due date of {due_date_text}. "
            f"{reminder_line}"
            "Please share a firm payment timeline or let us know if there is any issue on your side.\n\n"
            f"{tone_line}"
        )

    if assessment.escalation_level == EscalationLevel.MEDIUM:
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


def _build_subject_tts(
    extraction: ARExtractionLike,
    assessment: ARWorkflowAssessment,
) -> str:
    invoice_number_text = tts_safe_identifier(extraction.invoice_number, label="invoice")
    if assessment.payment_claim:
        return f"Follow-up on payment confirmation for {invoice_number_text}"
    if assessment.escalation_level == EscalationLevel.NONE:
        return f"Friendly reminder. {invoice_number_text} was due on {tts_safe_date_text(extraction.due_date)}"
    if assessment.escalation_level == EscalationLevel.LOW:
        return f"Second reminder. {invoice_number_text} remains unpaid"
    return f"Action requested. Overdue {invoice_number_text}"


def _build_followup_draft_tts(
    *,
    extraction: ARExtractionLike,
    assessment: ARWorkflowAssessment,
) -> str:
    customer_name = extraction.customer_name or "team"
    invoice_number_text = tts_safe_identifier(extraction.invoice_number, label="invoice number")
    amount_text = tts_safe_amount_text(extraction.amount, extraction.currency)
    due_date_text = tts_safe_date_text(extraction.due_date)
    tone_line = _tone_sentence(assessment.customer_policy.preferred_tone)

    if assessment.payment_claim:
        return (
            f"Hello {customer_name}. "
            f"This is a follow-up on {invoice_number_text} for {amount_text}. "
            "We have not matched the payment in our records yet. "
            "Please share the transfer date, transaction reference, and remittance advice so we can reconcile it."
            f" {tone_line}"
        )

    if assessment.escalation_level == EscalationLevel.NONE:
        return (
            f"Hello {customer_name}. "
            f"This is a quick reminder that {invoice_number_text} for {amount_text} was due on {due_date_text}. "
            "If payment has already been initiated, please share the transfer details. "
            "Otherwise, please let us know the expected payment date."
            f" {tone_line}"
        )

    if assessment.escalation_level == EscalationLevel.LOW:
        reminder_line = ""
        if (assessment.prior_reminders or 0) >= 1:
            reminder_line = "This follows our earlier reminder on the same invoice. "
        return (
            f"Hello {customer_name}. "
            f"{invoice_number_text} for {amount_text} remains unpaid after its due date of {due_date_text}. "
            f"{reminder_line}"
            "Please share a firm payment timeline or let us know if there is any issue on your side."
            f" {tone_line}"
        )

    if assessment.escalation_level == EscalationLevel.MEDIUM:
        return (
            f"Hello {customer_name}. "
            f"{invoice_number_text} for {amount_text} remains overdue since {due_date_text}. "
            "We have already followed up and still do not have a confirmed payment date. "
            "Please send immediate confirmation of status or share a payment plan so we can align next steps."
            f" {tone_line}"
        )

    return (
        f"Hello {customer_name}. "
        f"{invoice_number_text} for {amount_text} is now significantly overdue beyond {due_date_text}. "
        "We need urgent confirmation of payment status or a firm resolution plan today so this can be closed without further escalation."
        f" {tone_line}"
    )


def _estimate_confidence(
    context: GroundedPolicyContext,
    assessment: ARWorkflowAssessment,
) -> float:
    base = 0.9
    if assessment.payment_claim:
        base += 0.03
    if assessment.escalation_level in {EscalationLevel.MEDIUM, EscalationLevel.HIGH}:
        base -= 0.04
    if len(context.retrieval_hits) < 2:
        base -= 0.08
    if "missing_due_date" in assessment.trigger_codes or "missing_invoice_number" in assessment.trigger_codes:
        base -= 0.07
    if "repeated_reminders_high" in assessment.trigger_codes:
        base -= 0.03
    return max(0.45, min(round(base, 2), 0.99))


def _select_evidence(
    context: GroundedPolicyContext,
    extraction: ARExtractionLike,
    assessment: ARWorkflowAssessment,
) -> list[dict[str, str]]:
    if context.evidence_payloads:
        required_source_ids = _required_ar_source_ids(extraction, assessment)
        return _select_ordered_evidence(context.evidence_payloads, required_source_ids, limit=4)
    return [
        {
            "source_id": "context-summary",
            "source_title": "Grounded Policy Context",
            "excerpt": context.summary,
            "relevance_reason": "Fallback context summary when no KB evidence was returned.",
        }
    ]


def _required_ar_source_ids(
    extraction: ARExtractionLike,
    assessment: ARWorkflowAssessment,
) -> list[str]:
    source_ids = ["AR-ESCALATION-001"]
    if assessment.payment_claim:
        source_ids = ["AR-ESCALATION-002", "AR-TEMPLATE-004"]
    elif assessment.escalation_level == EscalationLevel.NONE:
        source_ids.append("AR-TEMPLATE-001")
    elif assessment.escalation_level == EscalationLevel.LOW:
        source_ids.append("AR-TEMPLATE-002")
    else:
        source_ids.append("AR-TEMPLATE-003")

    customer_source_id = _customer_source_id(extraction.customer_name)
    if customer_source_id:
        source_ids.append(customer_source_id)
    return source_ids


def _customer_source_id(customer_name: str | None) -> str | None:
    normalized = (customer_name or "").strip().lower()
    customer_ids = {
        "aster retail": "CUSTOMER-001",
        "horizon health group": "CUSTOMER-002",
        "meridian industrial": "CUSTOMER-003",
    }
    return customer_ids.get(normalized)


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
