"""OCR helpers for scanned or image-based PDF pages."""

from __future__ import annotations

from io import BytesIO
from typing import Any


def ocr_pdf_page(page: Any, page_index: int) -> tuple[str, list[str]]:
    """Run OCR on embedded page images when direct text extraction fails."""

    warnings: list[str] = []
    image_entries = getattr(page, "images", None)
    if image_entries is None:
        return "", [f"page_{page_index}_ocr_images_unavailable"]

    image_texts: list[str] = []

    for image_index, image_file in enumerate(image_entries, start=1):
        try:
            extracted_text = _ocr_image_blob(image_file.data)
        except Exception:
            warnings.append(f"page_{page_index}_image_{image_index}_ocr_failed")
            continue

        normalized_text = _normalize_ocr_text(extracted_text)
        if normalized_text:
            image_texts.append(normalized_text)
        else:
            warnings.append(f"page_{page_index}_image_{image_index}_ocr_empty")

    if not image_texts:
        warnings.append(f"page_{page_index}_ocr_no_text")
        return "", warnings

    return "\n\n".join(image_texts).strip(), warnings


def _ocr_image_blob(image_bytes: bytes) -> str:
    pytesseract = _resolve_pytesseract()
    image_class = _resolve_pil_image()

    with image_class.open(BytesIO(image_bytes)) as image:
        return pytesseract.image_to_string(image)


def _resolve_pytesseract():
    try:
        import pytesseract

        return pytesseract
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "pytesseract is not installed. Add it to the environment to enable OCR fallback."
        ) from exc


def _resolve_pil_image():
    try:
        from PIL import Image

        return Image
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Pillow is not installed. Add it to the environment to enable OCR fallback."
        ) from exc


def _normalize_ocr_text(raw_text: str) -> str:
    lines = [line.strip() for line in raw_text.replace("\r", "\n").split("\n")]
    filtered = [line for line in lines if line]
    return "\n".join(filtered).strip()
