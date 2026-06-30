from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from api.main import app


class ApiReliabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health_endpoint_reports_ok(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertGreaterEqual(payload["sample_count"], 1)

    def test_missing_sample_returns_structured_error(self) -> None:
        response = self.client.post(
            "/workflow/sample",
            json={"sample_id": "missing_case", "extractor_mode": "heuristic"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"]["code"], "sample_not_found")

    def test_invalid_extractor_mode_returns_structured_error(self) -> None:
        response = self.client.post(
            "/workflow/sample",
            json={"sample_id": "ap_001_clean_invoice", "extractor_mode": "unsafe"},
        )

        self.assertEqual(response.status_code, 400)
        detail = response.json()["detail"]
        self.assertEqual(detail["code"], "invalid_extractor_mode")
        self.assertIn("heuristic", detail["allowed"])

    def test_empty_upload_returns_structured_error(self) -> None:
        response = self.client.post(
            "/workflow/upload",
            data={"extractor_mode": "auto", "workflow_hint": "ap"},
            files={"file": ("empty.txt", b"", "text/plain")},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"]["code"], "empty_upload")

    def test_unsupported_upload_type_returns_fallback_hint(self) -> None:
        response = self.client.post(
            "/workflow/upload",
            data={"extractor_mode": "auto", "workflow_hint": "ap"},
            files={"file": ("invoice.exe", b"not a document", "application/octet-stream")},
        )

        self.assertEqual(response.status_code, 400)
        detail = response.json()["detail"]
        self.assertEqual(detail["code"], "unsupported_file_type")
        self.assertIn(".txt", detail["allowed_extensions"])
        self.assertIn("OCR", detail["ocr_note"])

    def test_text_upload_still_runs_workflow(self) -> None:
        content = b"""
        INVOICE
        Vendor: Test Vendor
        Invoice Number: TEST-100
        Amount: USD 250.00
        Due Date: 2026-07-15
        Purchase Order: PO-100
        Payment Terms: Net 30
        """

        response = self.client.post(
            "/workflow/upload",
            data={"extractor_mode": "heuristic", "workflow_hint": "ap"},
            files={"file": ("invoice.txt", content, "text/plain")},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("workflow_result", payload)
        self.assertEqual(payload["source"]["kind"], "upload")


if __name__ == "__main__":
    unittest.main()
