from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.ingest import read_document_text, supported_extensions


class FakePage:
    def __init__(self, text: str) -> None:
        self.text = text

    def extract_text(self) -> str:
        return self.text


class FakeReader:
    def __init__(self, _path: str) -> None:
        self.pages = [FakePage("Invoice number INV-101"), FakePage("")]


class PageAwareIngestionTests(unittest.TestCase):
    def test_pdf_preserves_native_and_ocr_page_locations(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".pdf") as source:
            with (
                patch("app.ingest.pdf_reader._resolve_pdf_reader", return_value=FakeReader),
                patch(
                    "app.ingest.pdf_reader.ocr_pdf_page",
                    return_value=("Purchase order PO-900", []),
                ),
            ):
                document = read_document_text(source.name)

        self.assertEqual(document.page_count, 2)
        self.assertEqual([page.page_number for page in document.pages], [1, 2])
        self.assertEqual(document.pages[0].extraction_method, "native")
        self.assertEqual(document.pages[1].extraction_method, "ocr")
        self.assertIn("Purchase order PO-900", document.pages[1].text)
        self.assertIn("page_2_used_ocr_fallback", document.pages[1].warnings)

    def test_image_is_a_single_ocr_page(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as source:
            source.write(b"fake-image")
            source_path = Path(source.name)
        try:
            with patch(
                "app.ingest.pdf_reader.ocr_image",
                return_value=("Vendor Northstar\nAmount USD 800", []),
            ):
                document = read_document_text(source_path)
        finally:
            source_path.unlink(missing_ok=True)

        self.assertEqual(document.source_type, "image")
        self.assertEqual(document.page_count, 1)
        self.assertEqual(document.pages[0].extraction_method, "ocr")
        self.assertIn("Vendor Northstar", document.text)

    def test_supported_extensions_include_validated_image_types(self) -> None:
        extensions = supported_extensions()

        self.assertIn(".png", extensions)
        self.assertIn(".jpg", extensions)
        self.assertIn(".jpeg", extensions)


if __name__ == "__main__":
    unittest.main()
