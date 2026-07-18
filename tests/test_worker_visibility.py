from __future__ import annotations

import time
import unittest

from app.queue import QueueOperationError
from app.worker.visibility import VisibilityHeartbeat


class RecordingVisibilityQueue:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []
        self.fail = False

    def change_visibility(
        self,
        *,
        receipt_handle: str,
        visibility_timeout_seconds: int,
    ) -> None:
        self.calls.append((receipt_handle, visibility_timeout_seconds))
        if self.fail:
            raise QueueOperationError("Queue operation failed.")


class VisibilityHeartbeatTests(unittest.TestCase):
    def test_heartbeat_extends_visibility_until_context_exits(self) -> None:
        queue = RecordingVisibilityQueue()

        with VisibilityHeartbeat(
            queue=queue,
            receipt_handle="receipt-123",
            visibility_timeout_seconds=60,
            interval_seconds=0.01,
        ) as heartbeat:
            time.sleep(0.035)

        self.assertGreaterEqual(len(queue.calls), 2)
        self.assertTrue(all(call == ("receipt-123", 60) for call in queue.calls))
        self.assertFalse(heartbeat.failed)
        stopped_count = len(queue.calls)
        time.sleep(0.02)
        self.assertEqual(len(queue.calls), stopped_count)

    def test_heartbeat_reports_provider_failure_and_stops(self) -> None:
        queue = RecordingVisibilityQueue()
        queue.fail = True

        with VisibilityHeartbeat(
            queue=queue,
            receipt_handle="receipt-123",
            visibility_timeout_seconds=60,
            interval_seconds=0.01,
        ) as heartbeat:
            time.sleep(0.03)

        self.assertTrue(heartbeat.failed)
        self.assertEqual(queue.calls, [("receipt-123", 60)])

    def test_interval_must_be_shorter_than_visibility_timeout(self) -> None:
        with self.assertRaises(ValueError):
            VisibilityHeartbeat(
                queue=RecordingVisibilityQueue(),
                receipt_handle="receipt-123",
                visibility_timeout_seconds=60,
                interval_seconds=60,
            )


if __name__ == "__main__":
    unittest.main()
