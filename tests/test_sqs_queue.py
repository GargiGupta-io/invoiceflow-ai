from __future__ import annotations

import json
import unittest
import uuid
from unittest.mock import patch

from botocore.exceptions import ClientError

from app.config import Settings
from app.queue import ProcessingMessage, QueueOperationError, SQSProcessingQueue


class FakeSQSClient:
    def __init__(self) -> None:
        self.requests: list[dict[str, str]] = []
        self.response: dict[str, str] = {"MessageId": "sqs-message-123"}
        self.error: Exception | None = None

    def send_message(self, **request):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.response


class SQSProcessingQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeSQSClient()
        self.queue_url = "https://sqs.ap-south-1.amazonaws.com/123456789012/invoiceflow"
        self.queue = SQSProcessingQueue(client=self.client, queue_url=self.queue_url)
        self.message = ProcessingMessage(
            job_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            request_id=uuid.uuid4(),
        )

    def test_send_uses_a_minimal_versioned_json_message(self) -> None:
        receipt = self.queue.send(self.message)

        self.assertEqual(receipt.message_id, "sqs-message-123")
        self.assertEqual(self.client.requests[0]["QueueUrl"], self.queue_url)
        payload = json.loads(self.client.requests[0]["MessageBody"])
        self.assertEqual(
            payload,
            {
                "document_id": str(self.message.document_id),
                "event_type": "document.processing.requested",
                "job_id": str(self.message.job_id),
                "organization_id": str(self.message.organization_id),
                "request_id": str(self.message.request_id),
                "schema_version": 1,
            },
        )
        for sensitive_field in (
            "authorization",
            "content",
            "filename",
            "presigned_url",
            "storage_key",
            "token",
        ):
            self.assertNotIn(sensitive_field, payload)

    def test_provider_error_is_replaced_with_safe_queue_error(self) -> None:
        self.client.error = ClientError(
            {
                "Error": {
                    "Code": "AccessDenied",
                    "Message": "secret queue URL and account details",
                }
            },
            "SendMessage",
        )

        with self.assertRaisesRegex(QueueOperationError, "Queue operation failed") as raised:
            self.queue.send(self.message)

        self.assertNotIn("secret queue", str(raised.exception))
        self.assertNotIn(self.queue_url, str(raised.exception))

    def test_missing_message_id_is_treated_as_a_failed_dispatch(self) -> None:
        self.client.response = {}

        with self.assertRaises(QueueOperationError):
            self.queue.send(self.message)

    def test_settings_build_an_sqs_client_with_aws_runtime_configuration(self) -> None:
        settings = Settings(
            _env_file=None,
            aws_region="eu-west-1",
            aws_endpoint_url="http://localhost:4566",
            sqs_queue_url=self.queue_url,
        )

        with patch("app.queue.sqs.boto3.client", return_value=self.client) as create_client:
            queue = SQSProcessingQueue.from_settings(settings)

        self.assertEqual(queue.queue_url, self.queue_url)
        create_client.assert_called_once()
        call = create_client.call_args
        self.assertEqual(call.args, ("sqs",))
        self.assertEqual(call.kwargs["region_name"], "eu-west-1")
        self.assertEqual(call.kwargs["endpoint_url"], "http://localhost:4566")


if __name__ == "__main__":
    unittest.main()
