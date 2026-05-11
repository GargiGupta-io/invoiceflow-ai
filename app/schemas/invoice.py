from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocumentType(str, Enum):
    INVOICE = "invoice"
    OVERDUE_EMAIL = "overdue_email"
    PAYMENT_CONFIRMATION = "payment_confirmation"


class CurrencyCode(str, Enum):
    USD = "USD"
    EUR = "EUR"
    INR = "INR"
    SGD = "SGD"
    GBP = "GBP"


class LineItem(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    description: str = Field(..., min_length=1, description="Human-readable line item description.")
    quantity: float | None = Field(default=None, ge=0, description="Detected quantity, when available.")
    unit_price: float | None = Field(default=None, ge=0, description="Detected unit price, when available.")
    line_total: float | None = Field(default=None, ge=0, description="Detected line total, when available.")


class InvoiceExtraction(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, use_enum_values=True)

    document_type: DocumentType = Field(..., description="The high-level document category.")
    vendor_name: str | None = Field(default=None, description="Detected vendor or sender name.")
    customer_name: str | None = Field(default=None, description="Detected customer or recipient name.")
    invoice_number: str | None = Field(default=None, description="Primary invoice identifier.")
    po_number: str | None = Field(default=None, description="Purchase order number, if present.")
    amount: float | None = Field(default=None, ge=0, description="Detected invoice amount.")
    currency: CurrencyCode | None = Field(default=None, description="Detected invoice currency.")
    issue_date: date | None = Field(default=None, description="Invoice issue date.")
    due_date: date | None = Field(default=None, description="Invoice due date.")
    payment_terms: str | None = Field(default=None, description="Detected payment terms text.")
    line_items: list[LineItem] = Field(default_factory=list, description="Detected line items.")
    source_text_excerpt: str = Field(..., min_length=20, description="Useful source excerpt supporting the extraction.")
    missing_fields: list[str] = Field(default_factory=list, description="Fields the extractor could not confidently fill.")
    extraction_warnings: list[str] = Field(default_factory=list, description="Non-fatal extraction issues or ambiguities.")

    @field_validator("vendor_name", "customer_name", "invoice_number", "po_number", "payment_terms")
    @classmethod
    def blank_strings_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("source_text_excerpt")
    @classmethod
    def excerpt_must_have_content(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 20:
            raise ValueError("source_text_excerpt must contain enough text to support extraction review.")
        return value

    @field_validator("missing_fields", "extraction_warnings")
    @classmethod
    def dedupe_string_lists(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for value in values:
            item = value.strip()
            if item and item not in seen:
                cleaned.append(item)
                seen.add(item)
        return cleaned
