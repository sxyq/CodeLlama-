"""Unified execution queue for the image service (single-GPU serialization).

One shared queue for POST /v1/images/generations and POST /v1/images/edits:
at most `max_concurrent` diffusion runs hold an execution slot; further
requests wait up to `queue_timeout_seconds`; beyond `max_pending` waiters a
request is rejected immediately (HTTP 429 QUEUE_FULL).

Order of guarantees (see IMAGE_WEBUI report §queue/GPU lock):
  request -> queue slot -> gpu.lock (inside MANAGER.ensure_loaded)
  -> Ollama/nvidia re-checks -> inference -> release slot

In-process only: state is memory-resident, restart drops pending waiters
(acceptable for an internal tool).
"""
from __future__ import annotations

import os
import threading
import time
from typing import Dict

MAX_CONCURRENT = int(os.environ.get("IMAGE_QUEUE_MAX_CONCURRENT", "1"))
MAX_PENDING = int(os.environ.get("IMAGE_QUEUE_MAX_PENDING", "8"))
QUEUE_TIMEOUT_SECONDS = float(os.environ.get("IMAGE_QUEUE_TIMEOUT_SECONDS", "480"))


class QueueFull(Exception):
    """More waiters than max_pending -> caller should answer 429 QUEUE_FULL."""


class QueueTimeout(Exception):
    """Waited longer than queue_timeout_seconds for an execution slot."""


class ImageQueue:
    def __init__(self, max_concurrent: int = MAX_CONCURRENT,
                 max_pending: int = MAX_PENDING,
                 timeout_seconds: float = QUEUE_TIMEOUT_SECONDS) -> None:
        self.max_concurrent = max_concurrent
        self.max_pending = max_pending
        self.timeout_seconds = timeout_seconds
        self._cond = threading.Condition()
        self._running = 0
        self._waiters: list[threading.Event] = []

    def acquire(self) -> None:
        """Take an execution slot; block up to timeout_seconds.

        Raises QueueFull when max_pending waiters already queued, and
        QueueTimeout when no slot frees up in time. A slot granted in the
        same instant as the timeout still counts as granted (never dropped).
        """
        deadline = time.monotonic() + self.timeout_seconds
        with self._cond:
            if self._running < self.max_concurrent and not self._waiters:
                self._running += 1
                return
            if len(self._waiters) >= self.max_pending:
                raise QueueFull(
                    f"queue is full: {len(self._waiters)} waiting "
                    f"(max_pending={self.max_pending})"
                )
            ev = threading.Event()
            self._waiters.append(ev)

        remaining = deadline - time.monotonic()
        granted = ev.wait(max(remaining, 0.0))

        with self._cond:
            if ev.is_set():
                # slot was transferred to us by release() (running already counted)
                return
            # timed out before any grant -> leave the queue
            try:
                self._waiters.remove(ev)
            except ValueError:
                # granted between wait() returning False and acquiring the lock
                if ev.is_set():
                    return
            raise QueueTimeout(
                f"no execution slot within {self.timeout_seconds:.0f}s"
            )

    def release(self) -> None:
        """Free the current slot and hand it to the oldest waiter, if any."""
        with self._cond:
            if self._running <= 0:
                return
            self._running -= 1
            if self._waiters:
                ev = self._waiters.pop(0)
                self._running += 1  # transfer the slot
                ev.set()

    def stats(self) -> Dict[str, int]:
        with self._cond:
            return {
                "running": self._running,
                "pending": len(self._waiters),
                "max_pending": self.max_pending,
            }


# Single process-wide queue: generations and edits share it by design.
IMAGE_QUEUE = ImageQueue()
