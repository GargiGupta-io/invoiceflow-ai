from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException, status

from app.config import get_settings
from app.storage.interface import ObjectStorage
from app.storage.s3 import S3ObjectStorage


@lru_cache
def get_object_storage() -> ObjectStorage:
    try:
        return S3ObjectStorage.from_settings(get_settings())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "storage_unavailable",
                "message": "Private document storage is not configured.",
            },
        ) from None
