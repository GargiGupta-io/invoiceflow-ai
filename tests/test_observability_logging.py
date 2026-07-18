from __future__ import annotations

import io
import json
import logging
import unittest
import uuid

from app.observability.logging import (
    JsonEventFormatter,
    RuntimeEventLogger,
    SensitiveDataFilter,
)


class StructuredLoggingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.output = io.StringIO()
        self.handler = logging.StreamHandler(self.output)
        self.handler.addFilter(SensitiveDataFilter())
        self.handler.setFormatter(JsonEventFormatter())
        self.logger = logging.getLogger(f"invoiceflow.test.{uuid.uuid4()}")
        self.logger.handlers = [self.handler]
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.events = RuntimeEventLogger(
            self.logger,
            service="worker",
            environment="test",
        )

    def test_nested_sensitive_fields_and_signed_urls_are_redacted(self) -> None:
        self.events.emit(
            "safe_event",
            request_id="request-123",
            authorization="Bearer secret-token",
            nested={
                "receipt_handle": "private-receipt",
                "download": "https://private.example/document?X-Amz-Signature=secret",
            },
        )

        payload = json.loads(self.output.getvalue())
        self.assertEqual(payload["event"], "safe_event")
        self.assertEqual(payload["request_id"], "request-123")
        self.assertEqual(payload["authorization"], "[REDACTED]")
        self.assertEqual(payload["nested"]["receipt_handle"], "[REDACTED]")
        self.assertEqual(
            payload["nested"]["download"],
            "https://private.example/document?[REDACTED]",
        )
        self.assertNotIn("secret-token", self.output.getvalue())
        self.assertNotIn("private-receipt", self.output.getvalue())

    def test_worker_event_contains_correlation_and_cloudwatch_metrics(self) -> None:
        request_id = uuid.uuid4()
        job_id = uuid.uuid4()

        self.events.worker_result(
            outcome="completed",
            duration_ms=1432.4567,
            request_id=request_id,
            job_id=job_id,
            message_id="message-123",
            receive_count=1,
        )

        payload = json.loads(self.output.getvalue())
        self.assertEqual(payload["event"], "document_processed")
        self.assertEqual(payload["request_id"], str(request_id))
        self.assertEqual(payload["job_id"], str(job_id))
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["outcome"], "completed")
        self.assertEqual(payload["WorkerSuccesses"], 1)
        self.assertEqual(payload["WorkerFailures"], 0)
        metrics = payload["_aws"]["CloudWatchMetrics"][0]
        self.assertEqual(metrics["Namespace"], "InvoiceFlow")
        self.assertEqual(metrics["Dimensions"], [["service", "environment"]])


if __name__ == "__main__":
    unittest.main()
