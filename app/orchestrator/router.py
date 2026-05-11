"""Deterministic workflow routing for AP and AR cases."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from ..schemas.decision import WorkflowType
from ..schemas.invoice import DocumentType, InvoiceExtraction


@dataclass(slots=True)
class WorkflowRoute:
    """Resolved workflow route plus the reasons behind it."""

    workflow_type: WorkflowType
    reason: str
    matched_signals: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def route_workflow(extraction: InvoiceExtraction) -> WorkflowRoute:
    """Route a structured extraction into AP or AR workflow deterministically."""

    matched_signals: list[str] = []

    if extraction.document_type == DocumentType.INVOICE:
        matched_signals.append("document_type:invoice")
        if extraction.vendor_name:
            matched_signals.append("vendor_name_present")
        if extraction.po_number:
            matched_signals.append("po_number_present")
        return WorkflowRoute(
            workflow_type=WorkflowType.AP,
            reason="Invoice documents follow the AP approval workflow.",
            matched_signals=matched_signals,
        )

    if extraction.document_type == DocumentType.OVERDUE_EMAIL:
        matched_signals.append("document_type:overdue_email")
        if extraction.customer_name:
            matched_signals.append("customer_name_present")
        return WorkflowRoute(
            workflow_type=WorkflowType.AR,
            reason="Overdue invoice communications follow the AR follow-up workflow.",
            matched_signals=matched_signals,
        )

    if extraction.document_type == DocumentType.PAYMENT_CONFIRMATION:
        matched_signals.append("document_type:payment_confirmation")
        if extraction.customer_name:
            matched_signals.append("customer_name_present")
        return WorkflowRoute(
            workflow_type=WorkflowType.AR,
            reason="Payment-confirmation cases are part of the AR collections and follow-up workflow.",
            matched_signals=matched_signals,
        )

    raise ValueError(f"Unsupported document type for routing: {extraction.document_type}")
