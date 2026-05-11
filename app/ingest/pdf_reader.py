"""Read invoice and finance workflow documents into normalized text."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .ocr import ocr_pdf_page

PDF_EXTENSIONS = {".pdf"}
TEXT_EXTENSIONS = {".txt", ".md"}


class IngestionError(Exception):
    """Raised when an input document cannot be read safely."""


@dataclass(slots=True)
class DocumentText:
    """Normalized document text ready for downstream extraction."""

    source_path: Path
    source_type: str
    text: str
    page_count: int | None = None
    warnings: list[str] = field(default_factory=list)


def supported_extensions() -> tuple[str, ...]:
    """Return the file types the ingestion layer can currently read."""

    return tuple(sorted(PDF_EXTENSIONS | TEXT_EXTENSIONS))


def read_document_text(path: str | Path) -> DocumentText:
    """Load a supported file and normalize it for extraction."""

    source_path = Path(path).expanduser().resolve()
    if not source_path.exists():
        raise IngestionError(f"Document does not exist: {source_path}")
    if not source_path.is_file():
        raise IngestionError(f"Document path is not a file: {source_path}")

    suffix = source_path.suffix.lower()
    if suffix in PDF_EXTENSIONS:
        return _read_pdf(source_path)
    if suffix in TEXT_EXTENSIONS:
        return _read_text_file(source_path)

    supported = ", ".join(supported_extensions())
    raise IngestionError(
        f"Unsupported document type '{suffix or '<none>'}'. Supported: {supported}"
    )


def _read_text_file(source_path: Path) -> DocumentText:
    raw_text = source_path.read_text(encoding="utf-8")
    text = _normalize_text(raw_text)
    warnings: list[str] = []

    if not text:
        warnings.append("empty_text_document")

    return DocumentText(
        source_path=source_path,
        source_type="text",
        text=text,
        page_count=1,
        warnings=warnings,
    )


def _read_pdf(source_path: Path) -> DocumentText:
    reader_class = _resolve_pdf_reader()
    reader = reader_class(str(source_path))

    page_texts: list[str] = []
    warnings: list[str] = []

    for page_index, page in enumerate(reader.pages, start=1):
        extracted_text = page.extract_text() or ""
        normalized_page_text = _normalize_text(extracted_text)
        if not normalized_page_text:
            warnings.append(f"page_{page_index}_no_extractable_text")
            ocr_text, ocr_warnings = ocr_pdf_page(page, page_index)
            warnings.extend(ocr_warnings)
            if ocr_text:
                page_texts.append(ocr_text)
                warnings.append(f"page_{page_index}_used_ocr_fallback")
                continue
        page_texts.append(normalized_page_text)

    text = "\n\n".join(part for part in page_texts if part).strip()
    if not text:
        warnings.append("pdf_text_extraction_empty")
        warnings.append("pdf_requires_ocr_or_manual_review")

    return DocumentText(
        source_path=source_path,
        source_type="pdf",
        text=text,
        page_count=len(reader.pages),
        warnings=_dedupe_preserve_order(warnings),
    )


def _resolve_pdf_reader():
    try:
        from pypdf import PdfReader

        return PdfReader
    except ModuleNotFoundError:
        pass

    try:
        from PyPDF2 import PdfReader

        return PdfReader
    except ModuleNotFoundError as exc:
        raise IngestionError(
            "No PDF reader dependency is installed. Add 'pypdf' or 'PyPDF2' to the environment."
        ) from exc


def _normalize_text(raw_text: str) -> str:
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n").replace("\ufeff", "")
    lines = [line.rstrip() for line in text.split("\n")]
    cleaned_lines: list[str] = []
    blank_streak = 0

    for line in lines:
        if line.strip():
            cleaned_lines.append(line.strip())
            blank_streak = 0
            continue

        blank_streak += 1
        if blank_streak <= 1:
            cleaned_lines.append("")

    return "\n".join(cleaned_lines).strip()


def _dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered
