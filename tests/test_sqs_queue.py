from __future__ import annotations

import json
import unittest
import uuid
from unittest.mock import patch

from botocore.exceptions import ClientError

from app.config import Settings
from app.queue import (
    ProcessingMessage,
    QueueMessageValidationError,
    QueueOperationError,
    SQSProcessingQueue,
)


class FakeSQSClient:
    def __init__(self) -> None:
        self.requests: list[dict[str, str]] = []
        self.response: dict[str, str] = {"MessageId": "sqs-message-123"}
        self.receive_response: dict = {"Messages": []}
        self.error: Exception | None = None

    def send_message(self, **request):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.response

    def receive_message(self, **request):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.receive_response

    def delete_message(self, **request):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return {}

    def change_message_visibility(self, **request):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return {}

    def get_queue_attributes(self, **request):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return {"Attributes": {"QueueArn": "arn:aws:sqs:region:account:queue"}}


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

    def test_health_check_reads_queue_attributes_and_redacts_failure(self) -> None:
        self.queue.check_health()
        self.assertEqual(
            self.client.requests[0],
            {"QueueUrl": self.queue_url, "AttributeNames": ["QueueArn"]},
        )

        self.client.error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "private queue detail"}},
            "GetQueueAttributes",
        )
        with self.assertRaisesRegex(QueueOperationError, "Queue operation failed") as raised:
            self.queue.check_health()
        self.assertNotIn("private queue", str(raised.exception))

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
        client_config = call.kwargs["config"]
        self.assertEqual(client_config.connect_timeout, 5)
        self.assertGreater(client_config.read_timeout, settings.sqs_wait_time_seconds)

    def test_processing_message_round_trips_through_strict_schema(self) -> None:
        parsed = ProcessingMessage.from_body(self.message.to_body())

        self.assertEqual(parsed, self.message)
        payload = json.loads(self.message.to_body())
        payload["unexpected"] = "field"
        with self.assertRaises(QueueMessageValidationError):
            ProcessingMessage.from_body(json.dumps(payload))
        payload.pop("unexpected")
        payload["schema_version"] = 2
        with self.assertRaises(QueueMessageValidationError):
            ProcessingMessage.from_body(json.dumps(payload))

    def test_receive_uses_long_polling_and_returns_receipt_handle(self) -> None:
        self.client.receive_response = {
            "Messages": [
                {
                    "MessageId": "received-123",
                    "ReceiptHandle": "receipt-secret-123",
                    "Body": self.message.to_body(),
                    "Attributes": {"ApproximateReceiveCount": "3"},
                }
            ]
        }

        received = self.queue.receive_one(
            wait_time_seconds=20,
            visibility_timeout_seconds=120,
        )

        self.assertIsNotNone(received)
        assert received is not None
        self.assertEqual(received.message_id, "received-123")
        self.assertEqual(received.receipt_handle, "receipt-secret-123")
        self.assertEqual(received.receive_count, 3)
        request = self.client.requests[0]
        self.assertEqual(request["MaxNumberOfMessages"], 1)
        self.assertEqual(request["WaitTimeSeconds"], 20)
        self.assertEqual(request["VisibilityTimeout"], 120)

    def test_empty_receive_returns_none(self) -> None:
        self.assertIsNone(
            self.queue.receive_one(
                wait_time_seconds=20,
                visibility_timeout_seconds=120,
            )
        )

    def test_delete_uses_receipt_handle_and_redacts_provider_failure(self) -> None:
        self.queue.delete(receipt_handle="receipt-secret-123")
        self.assertEqual(
            self.client.requests[0],
            {"QueueUrl": self.queue_url, "ReceiptHandle": "receipt-secret-123"},
        )

        self.client.error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "private receipt detail"}},
            "DeleteMessage",
        )
        with self.assertRaisesRegex(QueueOperationError, "Queue operation failed") as raised:
            self.queue.delete(receipt_handle="receipt-secret-123")
        self.assertNotIn("private receipt", str(raised.exception))

    def test_change_visibility_uses_receipt_handle_and_bounded_timeout(self) -> None:
        self.queue.change_visibility(
            receipt_handle="receipt-secret-123",
            visibility_timeout_seconds=90,
        )

        self.assertEqual(
            self.client.requests[0],
            {
                "QueueUrl": self.queue_url,
                "ReceiptHandle": "receipt-secret-123",
                "VisibilityTimeout": 90,
            },
        )
        with self.assertRaises(ValueError):
            self.queue.change_visibility(
                receipt_handle="receipt-secret-123",
                visibility_timeout_seconds=43201,
            )

    def test_change_visibility_redacts_provider_failure(self) -> None:
        self.client.error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "private queue detail"}},
            "ChangeMessageVisibility",
        )

        with self.assertRaisesRegex(QueueOperationError, "Queue operation failed") as raised:
            self.queue.change_visibility(
                receipt_handle="receipt-secret-123",
                visibility_timeout_seconds=60,
            )

        self.assertNotIn("private queue", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
