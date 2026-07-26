from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from api import main


class ReviewerUiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(main.app)

    def test_missing_reviewer_build_returns_structured_unavailable_response(self) -> None:
        with patch.object(main, "REVIEWER_INDEX", Path("/missing/reviewer/index.html")):
            response = self.client.get("/reviewer")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["code"], "reviewer_ui_unavailable")

    def test_reviewer_index_uses_browser_security_headers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            index_path = Path(temporary_directory) / "index.html"
            index_path.write_text("<!doctype html><title>Reviewer</title>", encoding="utf-8")
            with patch.object(main, "REVIEWER_INDEX", index_path):
                response = self.client.get("/reviewer/callback?code=private-code")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["referrer-policy"], "no-referrer")
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertIn("frame-ancestors 'none'", response.headers["content-security-policy"])
        self.assertNotIn("private-code", response.text)


if __name__ == "__main__":
    unittest.main()
