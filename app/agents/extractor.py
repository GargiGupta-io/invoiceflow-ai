"""Structured extraction agent for finance workflow documents."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ..ingest import DocumentText
from ..schemas.invoice import CurrencyCode, DocumentType, InvoiceExtraction, LineItem

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "extractor_v1.md"
REPAIR_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "extractor_repair_v1.md"
FIELD_ALIASES = {
    "vendor": "vendor_name",
    "customer": "customer_name",
    "bill to": "customer_name",
    "invoice number": "invoice_number",
    "po number": "po_number",
    "invoice amount": "amount",
    "currency": "currency",
    "issue date": "issue_date",
    "due date": "due_date",
    "payment terms": "payment_terms",
    "document_type": "document_type",
    "document type": "document_type",
}


class ExtractionError(Exception):
    """Raised when extraction cannot return valid structured output."""


@dataclass(slots=True)
class ExtractorAgent:
    """Convert ingested document text into the strict extraction schema."""

    mode: str = "auto"
    model: str | None = None
    prompt_path: Path = PROMPT_PATH
    repair_prompt_path: Path = REPAIR_PROMPT_PATH
    llm_client: Any | None = None
    excerpt_chars: int = 500
    max_validation_retries: int = 2

    def extract(self, document: DocumentText) -> InvoiceExtraction:
        """Extract structured fields from a loaded document."""

        mode = self.mode.lower().strip()
        if mode not in {"auto", "heuristic", "llm"}:
            raise ExtractionError(f"Unsupported extractor mode: {self.mode}")

        if mode == "heuristic":
            return self._extract_with_heuristics(document)
        if mode == "llm":
            return self._extract_with_llm(document)

        if self._has_llm_configuration():
            return self._extract_with_llm(document)
        return self._extract_with_heuristics(document)

    def _extract_with_llm(self, document: DocumentText) -> InvoiceExtraction:
        client = self.llm_client or self._build_default_llm_client()
        if client is None:
            raise ExtractionError(
                "LLM extraction requested but no OpenAI-compatible configuration was found."
            )

        payload = self._request_llm_extraction(client, document)
        return self._validate_with_retry(document, payload, client=client)

    def _extract_with_heuristics(self, document: DocumentText) -> InvoiceExtraction:
        fields = self._parse_key_value_fields(document.text)
        document_type = self._resolve_document_type(fields, document.text)
        warnings = list(document.warnings)

        payload = {
            "document_type": document_type.value,
            "vendor_name": fields.get("vendor_name"),
            "customer_name": fields.get("customer_name"),
            "invoice_number": fields.get("invoice_number"),
            "po_number": fields.get("po_number"),
            "amount": _parse_float(fields.get("amount")),
            "currency": _normalize_currency(fields.get("currency")),
            "issue_date": _parse_date_string(fields.get("issue_date"), warnings, "issue_date"),
            "due_date": _parse_date_string(fields.get("due_date"), warnings, "due_date"),
            "payment_terms": fields.get("payment_terms"),
            "line_items": self._parse_line_items(document.text) if document_type == DocumentType.INVOICE else [],
            "source_text_excerpt": self._make_excerpt(document.text),
            "missing_fields": [],
            "extraction_warnings": warnings,
        }

        payload["missing_fields"] = self._compute_missing_fields(document_type, payload)
        return self._validate_with_retry(document, payload)

    def _parse_key_value_fields(self, text: str) -> dict[str, str]:
        parsed: dict[str, str] = {}
        for line in text.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            normalized_key = key.strip().lower()
            mapped_field = FIELD_ALIASES.get(normalized_key)
            if mapped_field is None:
                continue
            parsed[mapped_field] = value.strip()
        return parsed

    def _resolve_document_type(self, fields: dict[str, str], text: str) -> DocumentType:
        raw_value = (fields.get("document_type") or "").strip().lower()
        if raw_value:
            try:
                return DocumentType(raw_value)
            except ValueError:
                pass

        lowered = text.lower()
        if "customer reply:" in lowered or "payment has already been initiated" in lowered:
            return DocumentType.PAYMENT_CONFIRMATION
        if "overdue days:" in lowered or "expected goal:" in lowered:
            return DocumentType.OVERDUE_EMAIL
        return DocumentType.INVOICE

    def _parse_line_items(self, text: str) -> list[LineItem]:
        lines = text.splitlines()
        in_section = False
        parsed_items: list[LineItem] = []

        for line in lines:
            stripped = line.strip()
            if stripped.lower() == "line items:":
                in_section = True
                continue
            if not in_section:
                continue
            if not stripped:
                break
            if not stripped.startswith("- "):
                continue

            item = self._parse_line_item_line(stripped[2:])
            if item is not None:
                parsed_items.append(item)

        return parsed_items

    def _parse_line_item_line(self, raw_line: str) -> LineItem | None:
        detailed_match = re.match(
            r"^(?P<description>.+?)\s+x\s+(?P<quantity>[\d,]+(?:\.\d+)?)\s+@\s+(?P<unit_price>[\d,]+(?:\.\d+)?)\s+=\s+(?P<line_total>[\d,]+(?:\.\d+)?)$",
            raw_line,
        )
        if detailed_match:
            return LineItem(
                description=detailed_match.group("description").strip(),
                quantity=_parse_float(detailed_match.group("quantity")),
                unit_price=_parse_float(detailed_match.group("unit_price")),
                line_total=_parse_float(detailed_match.group("line_total")),
            )

        simple_match = re.match(
            r"^(?P<description>.+?)\s+=\s+(?P<line_total>[\d,]+(?:\.\d+)?)$",
            raw_line,
        )
        if simple_match:
            return LineItem(
                description=simple_match.group("description").strip(),
                line_total=_parse_float(simple_match.group("line_total")),
            )

        return None

    def _compute_missing_fields(self, document_type: DocumentType, payload: dict[str, Any]) -> list[str]:
        required_fields = {
            DocumentType.INVOICE: [
                "vendor_name",
                "invoice_number",
                "amount",
                "currency",
                "due_date",
            ],
            DocumentType.OVERDUE_EMAIL: [
                "customer_name",
                "invoice_number",
                "amount",
                "currency",
                "due_date",
            ],
            DocumentType.PAYMENT_CONFIRMATION: [
                "customer_name",
                "invoice_number",
                "amount",
                "currency",
                "due_date",
            ],
        }

        missing: list[str] = []
        for field_name in required_fields[document_type]:
            value = payload.get(field_name)
            if value is None or value == "" or value == []:
                missing.append(field_name)
        return missing

    def _request_llm_extraction(self, client: Any, document: DocumentText) -> dict[str, Any]:
        prompt = self.prompt_path.read_text(encoding="utf-8")
        completion = client.chat.completions.create(
            model=self.model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": self._build_document_payload(document),
                },
            ],
        )

        content = completion.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise ExtractionError("LLM extraction returned no usable JSON content.")

        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            return self._repair_payload_with_llm(
                client=client,
                document=document,
                payload={},
                validation_error=f"invalid_json_response: {exc}",
            )

    def _validate_with_retry(
        self,
        document: DocumentText,
        payload: dict[str, Any],
        client: Any | None = None,
    ) -> InvoiceExtraction:
        working_payload = self._normalize_payload(document, payload)
        last_error: str | None = None

        for attempt in range(self.max_validation_retries + 1):
            try:
                return InvoiceExtraction.model_validate(working_payload)
            except ValidationError as exc:
                last_error = self._summarize_validation_error(exc)
                if attempt >= self.max_validation_retries:
                    raise ExtractionError(
                        f"Extraction failed schema validation after {attempt + 1} attempts: {last_error}"
                    ) from exc

                if client is not None:
                    repaired_payload = self._repair_payload_with_llm(
                        client=client,
                        document=document,
                        payload=working_payload,
                        validation_error=last_error,
                    )
                else:
                    repaired_payload = self._repair_payload_locally(
                        document=document,
                        payload=working_payload,
                        validation_error=last_error,
                        attempt=attempt + 1,
                    )

                working_payload = self._normalize_payload(
                    document,
                    repaired_payload,
                    extra_warnings=[f"schema_retry_{attempt + 1}"],
                )

        raise ExtractionError(f"Extraction validation did not converge: {last_error or 'unknown error'}")

    def _normalize_payload(
        self,
        document: DocumentText,
        payload: dict[str, Any],
        extra_warnings: list[str] | None = None,
    ) -> dict[str, Any]:
        normalized = dict(payload)
        warnings = _coerce_string_list(normalized.get("extraction_warnings"))
        missing_fields = _coerce_string_list(normalized.get("missing_fields"))

        normalized["document_type"] = self._normalize_document_type_value(
            normalized.get("document_type"),
            document.text,
        )
        normalized["vendor_name"] = _clean_optional_text(normalized.get("vendor_name"))
        normalized["customer_name"] = _clean_optional_text(normalized.get("customer_name"))
        normalized["invoice_number"] = _clean_optional_text(normalized.get("invoice_number"))
        normalized["po_number"] = _clean_optional_text(normalized.get("po_number"))
        normalized["payment_terms"] = _clean_optional_text(normalized.get("payment_terms"))
        normalized["amount"] = _coerce_float(normalized.get("amount"))
        normalized["currency"] = _normalize_currency(_clean_optional_text(normalized.get("currency")))
        normalized["issue_date"] = _coerce_date_value(
            normalized.get("issue_date"),
            warnings,
            "issue_date",
        )
        normalized["due_date"] = _coerce_date_value(
            normalized.get("due_date"),
            warnings,
            "due_date",
        )
        normalized["line_items"] = normalized.get("line_items") if isinstance(normalized.get("line_items"), list) else []
        normalized["source_text_excerpt"] = self._normalize_excerpt(
            normalized.get("source_text_excerpt"),
            document.text,
        )

        document_type = DocumentType(normalized["document_type"])
        normalized["missing_fields"] = _merge_string_lists(
            missing_fields,
            self._compute_missing_fields(document_type, normalized),
        )
        normalized["extraction_warnings"] = _merge_string_lists(
            warnings,
            document.warnings,
            extra_warnings or [],
        )
        return normalized

    def _repair_payload_locally(
        self,
        document: DocumentText,
        payload: dict[str, Any],
        validation_error: str,
        attempt: int,
    ) -> dict[str, Any]:
        repaired = dict(payload)
        repaired["source_text_excerpt"] = repaired.get("source_text_excerpt") or self._make_excerpt(
            document.text
        )
        repaired["line_items"] = repaired.get("line_items") if isinstance(repaired.get("line_items"), list) else []
        repaired["missing_fields"] = _merge_string_lists(
            _coerce_string_list(repaired.get("missing_fields")),
            self._compute_missing_fields(
                self._resolve_document_type({}, document.text),
                repaired,
            ),
        )
        repaired["extraction_warnings"] = _merge_string_lists(
            _coerce_string_list(repaired.get("extraction_warnings")),
            [f"local_repair_attempt_{attempt}"],
            [f"repair_reason:{validation_error.split(':', 1)[0].strip()}"],
        )
        return repaired

    def _repair_payload_with_llm(
        self,
        client: Any,
        document: DocumentText,
        payload: dict[str, Any],
        validation_error: str,
    ) -> dict[str, Any]:
        repair_prompt = self.repair_prompt_path.read_text(encoding="utf-8")
        payload_text = json.dumps(payload, indent=2, default=str)
        completion = client.chat.completions.create(
            model=self.model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": repair_prompt},
                {
                    "role": "user",
                    "content": (
                        f"validation_error:\n{validation_error}\n\n"
                        f"current_payload:\n{payload_text}\n\n"
                        f"{self._build_document_payload(document)}"
                    ),
                },
            ],
        )

        content = completion.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise ExtractionError("LLM repair returned no usable JSON content.")

        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise ExtractionError("LLM repair returned invalid JSON.") from exc

    def _build_document_payload(self, document: DocumentText) -> str:
        joined_warnings = ", ".join(document.warnings) if document.warnings else "none"
        return (
            f"source_type: {document.source_type}\n"
            f"page_count: {document.page_count}\n"
            f"ingestion_warnings: {joined_warnings}\n\n"
            f"document_text:\n{document.text}"
        )

    def _has_llm_configuration(self) -> bool:
        return self.llm_client is not None or bool(os.getenv("OPENAI_API_KEY"))

    def _build_default_llm_client(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None

        try:
            from openai import OpenAI

            return OpenAI(
                api_key=api_key,
                base_url=os.getenv("OPENAI_BASE_URL"),
            )
        except ModuleNotFoundError as exc:
            raise ExtractionError(
                "The openai package is not installed in the current environment."
            ) from exc

    def _normalize_document_type_value(self, raw_value: Any, text: str) -> str:
        if isinstance(raw_value, DocumentType):
            return raw_value.value
        if isinstance(raw_value, str):
            candidate = raw_value.strip().lower()
            try:
                return DocumentType(candidate).value
            except ValueError:
                pass
        return self._resolve_document_type({}, text).value

    def _normalize_excerpt(self, raw_excerpt: Any, text: str) -> str:
        excerpt = _clean_optional_text(raw_excerpt)
        if excerpt is None or len(excerpt) < 20:
            return self._make_excerpt(text)
        return excerpt

    def _make_excerpt(self, text: str) -> str:
        excerpt = text.strip().replace("\n", " ")
        excerpt = re.sub(r"\s+", " ", excerpt)
        if len(excerpt) < 20:
            return "Document text unavailable for extraction review"
        if len(excerpt) <= self.excerpt_chars:
            return excerpt
        return excerpt[: self.excerpt_chars].rstrip() + "..."

    def _summarize_validation_error(self, error: ValidationError) -> str:
        first_error = error.errors()[0] if error.errors() else None
        if first_error is None:
            return str(error)
        location = ".".join(str(part) for part in first_error.get("loc", []))
        message = first_error.get("msg", "validation error")
        return f"{location}: {message}"


def _parse_float(raw_value: str | None) -> float | None:
    if raw_value is None:
        return None
    cleaned = raw_value.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _normalize_currency(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None
    candidate = raw_value.strip().upper()
    allowed = {member.value for member in CurrencyCode}
    return candidate if candidate in allowed else None


def _clean_optional_text(raw_value: Any) -> str | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, str):
        cleaned = raw_value.strip()
        return cleaned or None
    return str(raw_value).strip() or None


def _coerce_float(raw_value: Any) -> float | None:
    if isinstance(raw_value, (int, float)):
        return float(raw_value)
    if isinstance(raw_value, str):
        return _parse_float(raw_value)
    return None


def _parse_date_string(raw_value: str | None, warnings: list[str], field_name: str) -> date | None:
    if raw_value is None:
        return None
    candidate = raw_value.strip()
    try:
        return date.fromisoformat(candidate)
    except ValueError:
        warnings.append(f"{field_name}_invalid_date_format")
        return None


def _coerce_date_value(raw_value: Any, warnings: list[str], field_name: str) -> date | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, date):
        return raw_value
    if isinstance(raw_value, str):
        return _parse_date_string(raw_value, warnings, field_name)
    warnings.append(f"{field_name}_unsupported_type")
    return None


def _coerce_string_list(raw_value: Any) -> list[str]:
    if raw_value is None:
        return []
    if isinstance(raw_value, list):
        values = raw_value
    else:
        values = [raw_value]
    cleaned: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            cleaned.append(text)
    return cleaned


def _merge_string_lists(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for value in group:
            item = value.strip()
            if item and item not in seen:
                merged.append(item)
                seen.add(item)
    return merged
