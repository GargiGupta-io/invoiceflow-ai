from __future__ import annotations

from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import Settings
from app.queue.interface import (
    ProcessingMessage,
    QueueDispatchReceipt,
    QueueOperationError,
    ReceivedQueueMessage,
)


class SQSProcessingQueue:
    def __init__(self, *, client: Any, queue_url: str) -> None:
        if not queue_url.strip():
            raise ValueError("SQS queue URL is required.")
        self.client = client
        self.queue_url = queue_url.strip()

    @classmethod
    def from_settings(cls, settings: Settings) -> SQSProcessingQueue:
        if not settings.sqs_configured:
            raise ValueError("SQS processing queue is not configured.")
        read_timeout_seconds = max(25, settings.sqs_wait_time_seconds + 5)
        client = boto3.client(
            "sqs",
            region_name=settings.aws_region,
            endpoint_url=settings.aws_endpoint_url or None,
            config=Config(
                connect_timeout=5,
                read_timeout=read_timeout_seconds,
                retries={"mode": "standard", "max_attempts": 4},
            ),
        )
        return cls(client=client, queue_url=settings.sqs_queue_url)

    def check_health(self) -> None:
        try:
            self.client.get_queue_attributes(
                QueueUrl=self.queue_url,
                AttributeNames=["QueueArn"],
            )
        except (BotoCoreError, ClientError):
            raise QueueOperationError("Queue operation failed.") from None

    def send(self, message: ProcessingMessage) -> QueueDispatchReceipt:
        try:
            response = self.client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=message.to_body(),
            )
        except (BotoCoreError, ClientError):
            raise QueueOperationError("Queue operation failed.") from None

        message_id = response.get("MessageId")
        if not isinstance(message_id, str) or not message_id:
            raise QueueOperationError("Queue operation failed.")
        return QueueDispatchReceipt(message_id=message_id)

    def receive_one(
        self,
        *,
        wait_time_seconds: int,
        visibility_timeout_seconds: int,
    ) -> ReceivedQueueMessage | None:
        if not 0 <= wait_time_seconds <= 20:
            raise ValueError("SQS wait time must be between 0 and 20 seconds.")
        if not 30 <= visibility_timeout_seconds <= 43200:
            raise ValueError("SQS visibility timeout must be between 30 seconds and 12 hours.")
        try:
            response = self.client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=wait_time_seconds,
                VisibilityTimeout=visibility_timeout_seconds,
                AttributeNames=["ApproximateReceiveCount"],
            )
        except (BotoCoreError, ClientError):
            raise QueueOperationError("Queue operation failed.") from None

        messages = response.get("Messages") or []
        if not messages:
            return None
        message = messages[0]
        message_id = message.get("MessageId")
        receipt_handle = message.get("ReceiptHandle")
        body = message.get("Body")
        if not all(isinstance(value, str) and value for value in (message_id, receipt_handle, body)):
            raise QueueOperationError("Queue operation failed.")
        try:
            receive_count = int(message.get("Attributes", {}).get("ApproximateReceiveCount", "1"))
        except (TypeError, ValueError):
            raise QueueOperationError("Queue operation failed.") from None
        if receive_count < 1:
            raise QueueOperationError("Queue operation failed.")
        return ReceivedQueueMessage(
            message_id=message_id,
            receipt_handle=receipt_handle,
            body=body,
            receive_count=receive_count,
        )

    def delete(self, *, receipt_handle: str) -> None:
        if not receipt_handle:
            raise ValueError("SQS receipt handle is required.")
        try:
            self.client.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
            )
        except (BotoCoreError, ClientError):
            raise QueueOperationError("Queue operation failed.") from None

    def change_visibility(
        self,
        *,
        receipt_handle: str,
        visibility_timeout_seconds: int,
    ) -> None:
        if not receipt_handle:
            raise ValueError("SQS receipt handle is required.")
        if not 0 <= visibility_timeout_seconds <= 43200:
            raise ValueError("SQS visibility timeout must be between 0 seconds and 12 hours.")
        try:
            self.client.change_message_visibility(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=visibility_timeout_seconds,
            )
        except (BotoCoreError, ClientError):
            raise QueueOperationError("Queue operation failed.") from None
