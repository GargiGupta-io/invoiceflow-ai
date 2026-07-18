from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException, status

from app.config import get_settings
from app.queue.interface import ProcessingQueue
from app.queue.sqs import SQSProcessingQueue


@lru_cache
def get_processing_queue() -> ProcessingQueue:
    try:
        return SQSProcessingQueue.from_settings(get_settings())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "processing_queue_unavailable",
                "message": "Document processing is not configured.",
            },
        ) from None
