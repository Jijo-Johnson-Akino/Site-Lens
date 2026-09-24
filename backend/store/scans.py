from __future__ import annotations

import threading
from typing import Protocol

from backend.schemas.scan import ScanRecord


class ScanRepository(Protocol):
    def create(self, record: ScanRecord) -> ScanRecord: ...
    def get(self, scan_id: str) -> ScanRecord | None: ...
    def save(self, record: ScanRecord) -> ScanRecord: ...
    def active_count(self) -> int: ...


class InMemoryScanStore:
    """Process-local store. Swap for Postgres later without changing ScanService."""

    def __init__(self) -> None:
        self._records: dict[str, ScanRecord] = {}
        self._lock = threading.Lock()

    def create(self, record: ScanRecord) -> ScanRecord:
        with self._lock:
            self._records[record.id] = record.model_copy(deep=True)
            return record.model_copy(deep=True)

    def get(self, scan_id: str) -> ScanRecord | None:
        with self._lock:
            record = self._records.get(scan_id)
            return record.model_copy(deep=True) if record else None

    def save(self, record: ScanRecord) -> ScanRecord:
        with self._lock:
            self._records[record.id] = record.model_copy(deep=True)
            return record.model_copy(deep=True)

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for record in self._records.values() if record.status in {"queued", "running"})
