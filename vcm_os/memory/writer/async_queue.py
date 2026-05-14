"""Async ingestion queue — batch-process events for higher throughput.

Instead of blocking on LLM extraction per event, this queue buffers events
and flushes them in batches.  Two modes:

- sync flush: call flush() explicitly (e.g. at end of session)
- auto flush: background timer flush every N seconds
"""
import threading
import time
from typing import Callable, List, Optional

from vcm_os.schemas import EventRecord, WriteReport


class AsyncIngestionQueue:
    """Buffers events and flushes them in batches.

    Usage:
        queue = AsyncIngestionQueue(writer.capture_event, batch_size=10, max_wait_seconds=5)
        queue.put(event)
        ...
        queue.flush()   # drain remaining
    """

    def __init__(
        self,
        handler: Callable[[EventRecord], WriteReport],
        batch_size: int = 10,
        max_wait_seconds: float = 5.0,
        auto_flush: bool = False,
    ):
        self.handler = handler
        self.batch_size = batch_size
        self.max_wait_seconds = max_wait_seconds
        self.auto_flush = auto_flush
        self._buffer: List[EventRecord] = []
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None
        self._total_flushed = 0
        if auto_flush:
            self._schedule_flush()

    def put(self, event: EventRecord) -> None:
        with self._lock:
            self._buffer.append(event)
            should_flush = len(self._buffer) >= self.batch_size
        if should_flush:
            self.flush()

    def flush(self) -> int:
        with self._lock:
            batch = self._buffer[:]
            self._buffer = []
        if not batch:
            return 0
        for event in batch:
            try:
                self.handler(event)
            except Exception:
                pass
        self._total_flushed += len(batch)
        if self.auto_flush:
            self._schedule_flush()
        return len(batch)

    def _schedule_flush(self) -> None:
        if self._timer:
            self._timer.cancel()
        self._timer = threading.Timer(self.max_wait_seconds, self.flush)
        self._timer.daemon = True
        self._timer.start()

    def close(self) -> int:
        if self._timer:
            self._timer.cancel()
        return self.flush()

    def stats(self) -> dict:
        with self._lock:
            buffered = len(self._buffer)
        return {
            "buffered": buffered,
            "total_flushed": self._total_flushed,
            "batch_size": self.batch_size,
            "max_wait_seconds": self.max_wait_seconds,
        }
