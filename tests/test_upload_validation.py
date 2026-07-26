from __future__ import annotations

import unittest
from io import BytesIO
from unittest.mock import patch

from PIL import Image
from pydantic import ValidationError
from pypdf import PdfWriter

from app.config import Settings
from app.ingest import UploadKind, UploadValidationError, UploadValidator


def build_pdf(*, page_count: int = 1, password: str | None = None) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=612, height=792)
    if password:
        writer.encrypt(password)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def build_image(*, image_format: str) -> bytes:
    output = BytesIO()
    with Image.new("RGB", (12, 8), color=(93, 151, 132)) as image:
        image.save(output, format=image_format)
    return output.getvalue()


class UploadValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = UploadValidator(max_bytes=1024 * 1024, max_pdf_pages=3)

    def test_valid_pdf_returns_normalized_metadata(self) -> None:
        content = build_pdf(page_count=2)

        result = self.validator.validate(
            filename="Quarterly Invoice.PDF",
            declared_content_type="application/pdf",
            content=content,
        )

        self.assertEqual(result.kind, UploadKind.PDF)
        self.assertEqual(result.content_type, "application/pdf")
        self.assertEqual(result.page_count, 2)
        self.assertEqual(result.safe_filename, "Quarterly Invoice.PDF")
        self.assertEqual(result.content, content)

    def test_valid_png_is_opened_by_image_parser(self) -> None:
        result = self.validator.validate(
            filename="invoice.png",
            declared_content_type="image/png",
            content=build_image(image_format="PNG"),
        )

        self.assertEqual(result.kind, UploadKind.PNG)
        self.assertEqual((result.image_width, result.image_height), (12, 8))
        self.assertEqual(result.page_count, 1)

    def test_valid_jpeg_accepts_content_type_parameters(self) -> None:
        result = self.validator.validate(
            filename="invoice.jpeg",
            declared_content_type="image/jpeg; charset=binary",
            content=build_image(image_format="JPEG"),
        )

        self.assertEqual(result.kind, UploadKind.JPEG)
        self.assertEqual(result.content_type, "image/jpeg")

    def test_original_path_is_removed_from_safe_metadata_filename(self) -> None:
        result = self.validator.validate(
            filename=r"C:\fakepath\July invoice (final).pdf",
            declared_content_type="application/pdf",
            content=build_pdf(),
        )

        self.assertEqual(result.original_filename, "July invoice (final).pdf")
        self.assertEqual(result.safe_filename, "July invoice _final_.pdf")

    def test_empty_upload_is_rejected(self) -> None:
        self.assert_validation_code(
            "empty_file",
            filename="invoice.pdf",
            content_type="application/pdf",
            content=b"",
        )

    def test_unsupported_extension_is_rejected(self) -> None:
        self.assert_validation_code(
            "extension_not_allowed",
            filename="invoice.txt",
            content_type="application/pdf",
            content=build_pdf(),
        )

    def test_unsupported_declared_content_type_is_rejected(self) -> None:
        self.assert_validation_code(
            "content_type_not_allowed",
            filename="invoice.pdf",
            content_type="application/octet-stream",
            content=build_pdf(),
        )

    def test_null_byte_in_filename_is_rejected(self) -> None:
        self.assert_validation_code(
            "filename_invalid",
            filename="invoice.pdf\x00.png",
            content_type="image/png",
            content=build_image(image_format="PNG"),
        )

    def test_spoofed_declared_content_type_is_rejected(self) -> None:
        self.assert_validation_code(
            "file_type_mismatch",
            filename="invoice.pdf",
            content_type="image/png",
            content=build_pdf(),
        )

    def test_extension_and_signature_mismatch_is_rejected(self) -> None:
        self.assert_validation_code(
            "file_type_mismatch",
            filename="invoice.png",
            content_type="image/png",
            content=build_pdf(),
        )

    def test_unknown_signature_is_rejected(self) -> None:
        self.assert_validation_code(
            "file_signature_invalid",
            filename="invoice.pdf",
            content_type="application/pdf",
            content=b"not a real document",
        )

    def test_corrupted_pdf_with_valid_header_is_rejected(self) -> None:
        self.assert_validation_code(
            "file_unreadable",
            filename="invoice.pdf",
            content_type="application/pdf",
            content=b"%PDF-1.7\ncorrupted",
        )

    def test_corrupted_png_with_valid_header_is_rejected(self) -> None:
        self.assert_validation_code(
            "file_unreadable",
            filename="invoice.png",
            content_type="image/png",
            content=b"\x89PNG\r\n\x1a\ncorrupted",
        )

    def test_image_decompression_bomb_is_rejected(self) -> None:
        with patch.object(Image, "MAX_IMAGE_PIXELS", 10):
            self.assert_validation_code(
                "file_unreadable",
                filename="invoice.png",
                content_type="image/png",
                content=build_image(image_format="PNG"),
            )

    def test_oversized_file_is_rejected_before_parsing(self) -> None:
        validator = UploadValidator(max_bytes=16, max_pdf_pages=3)

        with self.assertRaises(UploadValidationError) as context:
            validator.validate(
                filename="invoice.pdf",
                declared_content_type="application/pdf",
                content=build_pdf(),
            )

        self.assertEqual(context.exception.code, "file_too_large")

    def test_pdf_page_limit_is_enforced(self) -> None:
        self.assert_validation_code(
            "pdf_page_limit_exceeded",
            filename="invoice.pdf",
            content_type="application/pdf",
            content=build_pdf(page_count=4),
        )

    def test_encrypted_pdf_is_rejected(self) -> None:
        self.assert_validation_code(
            "encrypted_pdf",
            filename="invoice.pdf",
            content_type="application/pdf",
            content=build_pdf(password="private"),
        )

    def test_filename_length_limit_is_enforced(self) -> None:
        validator = UploadValidator(
            max_bytes=1024 * 1024,
            max_pdf_pages=3,
            max_filename_length=32,
        )

        with self.assertRaises(UploadValidationError) as context:
            validator.validate(
                filename=f"{'a' * 40}.pdf",
                declared_content_type="application/pdf",
                content=build_pdf(),
            )

        self.assertEqual(context.exception.code, "filename_invalid")

    def assert_validation_code(
        self,
        expected_code: str,
        *,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> None:
        with self.assertRaises(UploadValidationError) as context:
            self.validator.validate(
                filename=filename,
                declared_content_type=content_type,
                content=content,
            )
        self.assertEqual(context.exception.code, expected_code)


class UploadValidationSettingsTests(unittest.TestCase):
    def test_settings_create_validator_with_configured_limits(self) -> None:
        settings = Settings(
            _env_file=None,
            upload_max_bytes=2048,
            upload_max_pdf_pages=7,
            upload_max_filename_length=120,
        )

        validator = UploadValidator.from_settings(settings)

        self.assertEqual(validator.max_bytes, 2048)
        self.assertEqual(validator.max_pdf_pages, 7)
        self.assertEqual(validator.max_filename_length, 120)

    def test_invalid_upload_limits_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, upload_max_pdf_pages=0)


if __name__ == "__main__":
    unittest.main()
