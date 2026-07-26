from __future__ import annotations

import unittest
from unittest.mock import patch

from app.ingest import IngestionError
from app.worker import InvoiceFlowDocumentProcessor, PermanentDocumentProcessingError


class WorkerProcessorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.processor = InvoiceFlowDocumentProcessor(extractor_mode="heuristic")

    def test_image_enters_workflow_and_returns_page_metadata(self) -> None:
        with patch(
            "app.worker.processor.run_workflow_from_upload",
            return_value={
                "workflow_result": {"workflow_type": "accounts_payable"},
                "grounded_context": {"evidence_payloads": []},
                "_document_pages": [
                    {
                        "page_number": 1,
                        "text": "Invoice INV-100",
                        "extraction_method": "ocr",
                        "warnings": [],
                    }
                ],
            },
        ) as workflow:
            processed = self.processor.process(
                filename="invoice.png",
                content=b"image-bytes",
                content_type="image/png",
            )

        self.assertEqual(processed.pages[0]["extraction_method"], "ocr")
        workflow.assert_called_once_with(
            filename="invoice.png",
            content=b"image-bytes",
            extractor_mode="heuristic",
            include_document_pages=True,
        )

    def test_ingestion_failure_becomes_a_safe_permanent_error(self) -> None:
        with patch(
            "app.worker.processor.run_workflow_from_upload",
            side_effect=IngestionError("sensitive parser detail"),
        ):
            with self.assertRaises(PermanentDocumentProcessingError) as raised:
                self.processor.process(
                    filename="invoice.pdf",
                    content=b"pdf-bytes",
                    content_type="application/pdf",
                )

        self.assertEqual(raised.exception.code, "document_ingestion_failed")
        self.assertNotIn("sensitive parser", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
