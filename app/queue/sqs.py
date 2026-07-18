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
        client = boto3.client(
            "sqs",
            region_name=settings.aws_region,
            endpoint_url=settings.aws_endpoint_url or None,
            config=Config(
                connect_timeout=5,
                read_timeout=10,
                retries={"mode": "standard", "max_attempts": 4},
            ),
        )
        return cls(client=client, queue_url=settings.sqs_queue_url)

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
