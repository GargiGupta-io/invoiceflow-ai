from __future__ import annotations

import unittest
from unittest.mock import patch

from app.ingest import IngestionError
from app.worker import InvoiceFlowDocumentProcessor, PermanentDocumentProcessingError


class WorkerProcessorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.processor = InvoiceFlowDocumentProcessor(extractor_mode="heuristic")

    def test_image_requires_ocr_without_entering_the_workflow(self) -> None:
        with patch("app.worker.processor.run_workflow_from_upload") as workflow:
            with self.assertRaises(PermanentDocumentProcessingError) as raised:
                self.processor.process(
                    filename="invoice.png",
                    content=b"image-bytes",
                    content_type="image/png",
                )

        workflow.assert_not_called()
        self.assertEqual(raised.exception.code, "document_ocr_required")

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
