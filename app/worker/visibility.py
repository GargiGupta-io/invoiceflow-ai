from __future__ import annotations

from threading import Event, Thread

from app.queue import ProcessingQueue, QueueOperationError


class VisibilityHeartbeat:
    """Keep one in-flight SQS message hidden while its worker is active."""

    def __init__(
        self,
        *,
        queue: ProcessingQueue,
        receipt_handle: str,
        visibility_timeout_seconds: int,
        interval_seconds: float,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("Visibility heartbeat interval must be positive.")
        if interval_seconds >= visibility_timeout_seconds:
            raise ValueError("Visibility heartbeat interval must be shorter than its timeout.")
        self.queue = queue
        self.receipt_handle = receipt_handle
        self.visibility_timeout_seconds = visibility_timeout_seconds
        self.interval_seconds = interval_seconds
        self._stop = Event()
        self._failed = Event()
        self._thread: Thread | None = None

    @property
    def failed(self) -> bool:
        return self._failed.is_set()

    def __enter__(self) -> VisibilityHeartbeat:
        self._thread = Thread(
            target=self._run,
            name="invoiceflow-sqs-visibility",
            daemon=True,
        )
        self._thread.start()
        return self

    def __exit__(self, *_error: object) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join()

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            try:
                self.queue.change_visibility(
                    receipt_handle=self.receipt_handle,
                    visibility_timeout_seconds=self.visibility_timeout_seconds,
                )
            except QueueOperationError:
                self._failed.set()
                return
