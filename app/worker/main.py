from __future__ import annotations

from time import sleep

from app.config import Settings, get_settings
from app.db.session import create_database
from app.queue import SQSProcessingQueue
from app.storage import S3ObjectStorage
from app.worker.processor import InvoiceFlowDocumentProcessor
from app.worker.service import DocumentWorker, WorkerExecutionError


def build_worker(settings: Settings | None = None) -> DocumentWorker:
    resolved = settings or get_settings()
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
    )


def main() -> None:
    worker = build_worker()
    while True:
        try:
            worker.run_once()
        except WorkerExecutionError:
            sleep(1)


if __name__ == "__main__":
    main()
