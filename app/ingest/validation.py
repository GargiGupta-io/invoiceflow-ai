from __future__ import annotations

import re
import warnings
from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO
from pathlib import PurePosixPath

from PIL import Image
from pypdf import PdfReader

from app.config import Settings


PDF_SIGNATURE = b"%PDF-"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8\xff"


class UploadKind(StrEnum):
    PDF = "pdf"
    PNG = "png"
    JPEG = "jpeg"


@dataclass(frozen=True)
class UploadType:
    kind: UploadKind
    extensions: frozenset[str]
    content_type: str
    signature: bytes
    parser_format: str | None = None


UPLOAD_TYPES = (
    UploadType(
        kind=UploadKind.PDF,
        extensions=frozenset({".pdf"}),
        content_type="application/pdf",
        signature=PDF_SIGNATURE,
    ),
    UploadType(
        kind=UploadKind.PNG,
        extensions=frozenset({".png"}),
        content_type="image/png",
        signature=PNG_SIGNATURE,
        parser_format="PNG",
    ),
    UploadType(
        kind=UploadKind.JPEG,
        extensions=frozenset({".jpg", ".jpeg"}),
        content_type="image/jpeg",
        signature=JPEG_SIGNATURE,
        parser_format="JPEG",
    ),
)


class UploadValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ValidatedUpload:
    content: bytes
    original_filename: str
    safe_filename: str
    kind: UploadKind
    content_type: str
    size_bytes: int
    page_count: int
    image_width: int | None = None
    image_height: int | None = None


class UploadValidator:
    def __init__(
        self,
        *,
        max_bytes: int = 10 * 1024 * 1024,
        max_pdf_pages: int = 25,
        max_filename_length: int = 255,
    ) -> None:
        if max_bytes < 1 or max_pdf_pages < 1 or max_filename_length < 1:
            raise ValueError("Upload validation limits must be positive.")
        self.max_bytes = max_bytes
        self.max_pdf_pages = max_pdf_pages
        self.max_filename_length = max_filename_length

    @classmethod
    def from_settings(cls, settings: Settings) -> UploadValidator:
        return cls(
            max_bytes=settings.upload_max_bytes,
            max_pdf_pages=settings.upload_max_pdf_pages,
            max_filename_length=settings.upload_max_filename_length,
        )

    def validate(
        self,
        *,
        filename: str,
        declared_content_type: str,
        content: bytes,
    ) -> ValidatedUpload:
        original_filename, safe_filename = self._validate_filename(filename)
        if not content:
            raise UploadValidationError("empty_file", "The uploaded file is empty.")
        if len(content) > self.max_bytes:
            raise UploadValidationError(
                "file_too_large",
                f"The uploaded file exceeds the {self.max_bytes}-byte limit.",
            )

        extension = PurePosixPath(safe_filename).suffix.lower()
        extension_type = self._type_for_extension(extension)
        content_type = self._normalize_content_type(declared_content_type)
        declared_type = self._type_for_content_type(content_type)
        signature_type = self._type_for_signature(content)

        if declared_type is None:
            raise UploadValidationError(
                "content_type_not_allowed",
                "Only PDF, PNG, and JPEG uploads are accepted.",
            )
        if signature_type is None:
            raise UploadValidationError(
                "file_signature_invalid",
                "The file signature does not match an accepted document type.",
            )
        if not (extension_type == declared_type == signature_type):
            raise UploadValidationError(
                "file_type_mismatch",
                "The filename, content type, and file signature do not agree.",
            )

        if signature_type.kind is UploadKind.PDF:
            page_count = self._validate_pdf(content)
            return ValidatedUpload(
                content=content,
                original_filename=original_filename,
                safe_filename=safe_filename,
                kind=signature_type.kind,
                content_type=signature_type.content_type,
                size_bytes=len(content),
                page_count=page_count,
            )

        width, height = self._validate_image(content, signature_type)
        return ValidatedUpload(
            content=content,
            original_filename=original_filename,
            safe_filename=safe_filename,
            kind=signature_type.kind,
            content_type=signature_type.content_type,
            size_bytes=len(content),
            page_count=1,
            image_width=width,
            image_height=height,
        )

    def _validate_filename(self, filename: str) -> tuple[str, str]:
        if not filename or "\x00" in filename:
            raise UploadValidationError("filename_invalid", "A valid filename is required.")

        submitted_filename = filename.strip()
        basename = submitted_filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
        if not basename or len(basename) > self.max_filename_length:
            raise UploadValidationError(
                "filename_invalid",
                f"The filename must be between 1 and {self.max_filename_length} characters.",
            )

        safe_filename = re.sub(r"[^A-Za-z0-9._ -]", "_", basename)
        safe_filename = safe_filename.lstrip(". -").strip()
        if not safe_filename:
            raise UploadValidationError("filename_invalid", "A valid filename is required.")

        extension = PurePosixPath(safe_filename).suffix.lower()
        if self._type_for_extension(extension) is None:
            raise UploadValidationError(
                "extension_not_allowed",
                "Only .pdf, .png, .jpg, and .jpeg files are accepted.",
            )
        return basename, safe_filename

    def _validate_pdf(self, content: bytes) -> int:
        try:
            reader = PdfReader(BytesIO(content), strict=True)
            if reader.is_encrypted:
                raise UploadValidationError(
                    "encrypted_pdf",
                    "Password-protected PDFs cannot be processed.",
                )
            page_count = len(reader.pages)
        except UploadValidationError:
            raise
        except Exception:
            raise UploadValidationError(
                "file_unreadable",
                "The PDF could not be opened by the document parser.",
            ) from None

        if page_count < 1:
            raise UploadValidationError(
                "file_unreadable",
                "The PDF does not contain any readable pages.",
            )
        if page_count > self.max_pdf_pages:
            raise UploadValidationError(
                "pdf_page_limit_exceeded",
                f"The PDF exceeds the {self.max_pdf_pages}-page limit.",
            )
        return page_count

    @staticmethod
    def _validate_image(content: bytes, upload_type: UploadType) -> tuple[int, int]:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(content)) as image:
                    if image.format != upload_type.parser_format:
                        raise UploadValidationError(
                            "file_type_mismatch",
                            "The image parser reported a different file type.",
                        )
                    width, height = image.size
                    image.verify()
        except UploadValidationError:
            raise
        except Exception:
            raise UploadValidationError(
                "file_unreadable",
                "The image could not be opened by the image parser.",
            ) from None

        if width < 1 or height < 1:
            raise UploadValidationError(
                "file_unreadable",
                "The image dimensions are invalid.",
            )
        return width, height

    @staticmethod
    def _normalize_content_type(content_type: str) -> str:
        return (content_type or "").split(";", 1)[0].strip().lower()

    @staticmethod
    def _type_for_extension(extension: str) -> UploadType | None:
        return next(
            (upload_type for upload_type in UPLOAD_TYPES if extension in upload_type.extensions),
            None,
        )

    @staticmethod
    def _type_for_content_type(content_type: str) -> UploadType | None:
        return next(
            (
                upload_type
                for upload_type in UPLOAD_TYPES
                if content_type == upload_type.content_type
            ),
            None,
        )

    @staticmethod
    def _type_for_signature(content: bytes) -> UploadType | None:
        return next(
            (
                upload_type
                for upload_type in UPLOAD_TYPES
                if content.startswith(upload_type.signature)
            ),
            None,
        )
