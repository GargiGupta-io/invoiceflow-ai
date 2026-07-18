from __future__ import annotations

import logging
from time import sleep

from app.config import Settings, get_settings
from app.db.session import create_database
from app.observability.logging import RuntimeEventLogger, configure_logging
from app.queue import SQSProcessingQueue
from app.storage import S3ObjectStorage
from app.worker.processor import InvoiceFlowDocumentProcessor
from app.worker.service import DocumentWorker, WorkerExecutionError


def build_worker(settings: Settings | None = None) -> DocumentWorker:
    resolved = settings or get_settings()
    event_logger = RuntimeEventLogger(
        logging.getLogger("invoiceflow.worker"),
        service="worker",
        environment=resolved.app_env,
        metric_namespace=resolved.cloudwatch_metric_namespace,
    )
    return DocumentWorker(
        database=create_database(resolved),
        queue=SQSProcessingQueue.from_settings(resolved),
        storage=S3ObjectStorage.from_settings(resolved),
        processor=InvoiceFlowDocumentProcessor(
            extractor_mode=resolved.worker_extractor_mode
        ),
        quarantine_prefix=resolved.s3_quarantine_prefix,
        validated_prefix=resolved.s3_validated_prefix,
        max_document_bytes=resolved.upload_max_bytes,
        wait_time_seconds=resolved.sqs_wait_time_seconds,
        visibility_timeout_seconds=resolved.sqs_visibility_timeout_seconds,
        visibility_heartbeat_seconds=resolved.sqs_visibility_heartbeat_seconds,
        retry_base_delay_seconds=resolved.sqs_retry_base_delay_seconds,
        retry_max_delay_seconds=resolved.sqs_retry_max_delay_seconds,
        redrive_max_receive_count=resolved.sqs_redrive_max_receive_count,
        stale_job_seconds=resolved.worker_stale_job_seconds,
        event_logger=event_logger,
    )


def main() -> None:
    settings = get_settings()
    configure_logging(level=settings.log_level)
    worker = build_worker(settings)
    while True:
        try:
            worker.run_once()
        except WorkerExecutionError:
            sleep(1)


if __name__ == "__main__":
    main()
