from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from api.main import app, get_readiness_checker
from app.db.session import create_database
from app.observability import DependencyStatus, ReadinessChecker
from app.queue import QueueOperationError
from app.storage import StorageOperationError


class HealthDependency:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls = 0

    def check_health(self) -> None:
        self.calls += 1
        if self.error is not None:
            raise self.error


class ReadinessCheckerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = create_database(database_url="sqlite://")

    def tearDown(self) -> None:
        self.database.dispose()

    def test_ready_requires_database_storage_and_queue(self) -> None:
        storage = HealthDependency()
        queue = HealthDependency()
        report = ReadinessChecker(
            database=self.database,
            storage_factory=lambda: storage,
            queue_factory=lambda: queue,
        ).check()

        self.assertTrue(report.ready)
        self.assertEqual(report.checks["database"].status, DependencyStatus.READY)
        self.assertEqual(report.checks["object_storage"].status, DependencyStatus.READY)
        self.assertEqual(report.checks["processing_queue"].status, DependencyStatus.READY)
        self.assertEqual(storage.calls, 1)
        self.assertEqual(queue.calls, 1)

    def test_missing_or_failed_dependencies_return_only_safe_states(self) -> None:
        report = ReadinessChecker(
            database=self.database,
            storage_factory=lambda: HealthDependency(
                StorageOperationError("private bucket detail")
            ),
            queue_factory=None,
        ).check()

        payload = report.to_dict()
        self.assertFalse(report.ready)
        self.assertEqual(payload["checks"]["object_storage"], {"status": "unavailable"})
        self.assertEqual(payload["checks"]["processing_queue"], {"status": "not_configured"})
        self.assertNotIn("private bucket", str(payload))


class HealthEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = create_database(database_url="sqlite://")
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.database.dispose()

    def test_liveness_does_not_probe_external_dependencies(self) -> None:
        response = self.client.get("/health/live")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "service": "invoiceflow-api"},
        )

    def test_readiness_returns_200_only_when_every_dependency_is_ready(self) -> None:
        app.dependency_overrides[get_readiness_checker] = lambda: ReadinessChecker(
            database=self.database,
            storage_factory=lambda: HealthDependency(),
            queue_factory=lambda: HealthDependency(),
        )

        response = self.client.get("/health/ready")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ready")

    def test_readiness_returns_503_without_exposing_provider_errors(self) -> None:
        app.dependency_overrides[get_readiness_checker] = lambda: ReadinessChecker(
            database=self.database,
            storage_factory=lambda: HealthDependency(),
            queue_factory=lambda: HealthDependency(
                QueueOperationError("secret queue URL")
            ),
        )

        response = self.client.get("/health/ready")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "not_ready")
        self.assertEqual(
            response.json()["checks"]["processing_queue"],
            {"status": "unavailable"},
        )
        self.assertNotIn("secret queue", response.text)


if __name__ == "__main__":
    unittest.main()
