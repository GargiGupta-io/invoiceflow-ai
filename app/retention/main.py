from __future__ import annotations

from app.config import get_settings
from app.db.session import create_database
from app.retention import DocumentDeletionService, RetentionDeletionWorker
from app.storage.s3 import S3ObjectStorage


def main() -> int:
    settings = get_settings()
    database = create_database(settings)
    storage = S3ObjectStorage.from_settings(settings)
    service = DocumentDeletionService(
        storage=storage,
        quarantine_prefix=settings.s3_quarantine_prefix,
        validated_prefix=settings.s3_validated_prefix,
    )
    worker = RetentionDeletionWorker(
        database=database,
        deletion_service=service,
        batch_size=settings.retention_delete_batch_size,
    )
    try:
        result = worker.run_once()
    finally:
        database.dispose()
    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
