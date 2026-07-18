from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from sqlalchemy import text

from app.db.session import Database
from app.queue.interface import ProcessingQueue
from app.storage.interface import ObjectStorage


class DependencyStatus(str, Enum):
    READY = "ready"
    UNAVAILABLE = "unavailable"
    NOT_CONFIGURED = "not_configured"


@dataclass(frozen=True)
class DependencyCheck:
    status: DependencyStatus

    def to_dict(self) -> dict[str, str]:
        return {"status": self.status.value}


@dataclass(frozen=True)
class ReadinessReport:
    checks: dict[str, DependencyCheck]

    @property
    def ready(self) -> bool:
        return all(check.status == DependencyStatus.READY for check in self.checks.values())

    def to_dict(self) -> dict[str, object]:
        return {
            "status": "ready" if self.ready else "not_ready",
            "checks": {name: check.to_dict() for name, check in self.checks.items()},
        }


class ReadinessChecker:
    def __init__(
        self,
        *,
        database: Database,
        storage_factory: Callable[[], ObjectStorage] | None,
        queue_factory: Callable[[], ProcessingQueue] | None,
    ) -> None:
        self.database = database
        self.storage_factory = storage_factory
        self.queue_factory = queue_factory

    def check(self) -> ReadinessReport:
        return ReadinessReport(
            checks={
                "database": self._database_check(),
                "object_storage": self._storage_check(),
                "processing_queue": self._queue_check(),
            }
        )

    def _database_check(self) -> DependencyCheck:
        try:
            with self.database.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception:
            return DependencyCheck(DependencyStatus.UNAVAILABLE)
        return DependencyCheck(DependencyStatus.READY)

    def _storage_check(self) -> DependencyCheck:
        if self.storage_factory is None:
            return DependencyCheck(DependencyStatus.NOT_CONFIGURED)
        try:
            self.storage_factory().check_health()
        except Exception:
            return DependencyCheck(DependencyStatus.UNAVAILABLE)
        return DependencyCheck(DependencyStatus.READY)

    def _queue_check(self) -> DependencyCheck:
        if self.queue_factory is None:
            return DependencyCheck(DependencyStatus.NOT_CONFIGURED)
        try:
            self.queue_factory().check_health()
        except Exception:
            return DependencyCheck(DependencyStatus.UNAVAILABLE)
        return DependencyCheck(DependencyStatus.READY)
