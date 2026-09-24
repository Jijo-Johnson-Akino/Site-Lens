"""In-memory screenshot blobs. API responses expose URLs, never filesystem paths."""

from __future__ import annotations

import threading
from typing import Protocol


class ScreenshotRepository(Protocol):
    def put(self, scan_id: str, viewport: str, data: bytes) -> None: ...
    def get(self, scan_id: str, viewport: str) -> bytes | None: ...


class InMemoryScreenshotStore:
    def __init__(self, max_bytes: int = 8 * 1024 * 1024, max_per_scan: int = 12) -> None:
        self._data: dict[tuple[str, str], bytes] = {}
        self._lock = threading.Lock()
        self._max_bytes = max_bytes
        self._max_per_scan = max_per_scan

    def put(self, scan_id: str, viewport: str, data: bytes) -> None:
        if not data or len(data) > self._max_bytes:
            return
        key = (scan_id, viewport)
        with self._lock:
            existing = [name for (sid, name) in self._data if sid == scan_id]
            if key not in self._data and len(existing) >= self._max_per_scan:
                return
            self._data[key] = data

    def get(self, scan_id: str, viewport: str) -> bytes | None:
        with self._lock:
            return self._data.get((scan_id, viewport))
