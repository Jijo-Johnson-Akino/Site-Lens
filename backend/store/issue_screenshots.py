"""Issue screenshot blobs on disk plus an in-memory cache. URLs are API paths, never filesystem paths."""

from __future__ import annotations

import re
import threading
import time
from pathlib import Path

from backend.config import ISSUE_SCREENSHOT_DIR, ISSUE_SCREENSHOT_MAX_PER_SCAN, ISSUE_SCREENSHOT_TTL_DAYS

SAFE = re.compile(r"[^a-zA-Z0-9._-]+")
MAX_BYTES = 8 * 1024 * 1024
TTL_SECONDS = ISSUE_SCREENSHOT_TTL_DAYS * 24 * 60 * 60


def _safe(value: str) -> str:
    cleaned = SAFE.sub("_", value).strip("._") or "file"
    return cleaned[:80]


class IssueScreenshotStore:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or ISSUE_SCREENSHOT_DIR
        self._data: dict[tuple[str, str], tuple[bytes, str, float]] = {}
        self._lock = threading.Lock()

    def url_for(self, scan_id: str, issue_id: str) -> str:
        return f"/api/scans/{scan_id}/issues/{issue_id}/screenshot"

    def put(self, scan_id: str, issue_id: str, data: bytes, content_type: str = "image/webp") -> str | None:
        if not data or len(data) > MAX_BYTES:
            return None
        key = (scan_id, issue_id)
        now = time.time()
        with self._lock:
            self._purge_locked(now)
            existing = [issue for (sid, issue) in self._data if sid == scan_id]
            if key not in self._data and len(existing) >= ISSUE_SCREENSHOT_MAX_PER_SCAN:
                return None
            self._data[key] = (data, content_type, now)
        self._write_file(scan_id, issue_id, data)
        return self.url_for(scan_id, issue_id)

    def get(self, scan_id: str, issue_id: str) -> tuple[bytes, str] | None:
        now = time.time()
        with self._lock:
            row = self._data.get((scan_id, issue_id))
            if row:
                data, content_type, created = row
                if now - created > TTL_SECONDS:
                    self._data.pop((scan_id, issue_id), None)
                    self._delete_file(scan_id, issue_id)
                    return None
                return data, content_type
        disk = self._read_file(scan_id, issue_id)
        if disk is None:
            return None
        data, mtime = disk
        if now - mtime > TTL_SECONDS:
            self._delete_file(scan_id, issue_id)
            return None
        with self._lock:
            self._data[(scan_id, issue_id)] = (data, "image/webp" if data[:4] == b"RIFF" else "image/png", mtime)
        return data, "image/webp" if data[:4] == b"RIFF" else "image/png"

    def delete_scan(self, scan_id: str) -> None:
        with self._lock:
            for key in [item for item in self._data if item[0] == scan_id]:
                self._data.pop(key, None)
        folder = self._folder(scan_id)
        if folder.exists():
            for path in folder.glob("*"):
                try:
                    path.unlink()
                except OSError:
                    pass
            try:
                folder.rmdir()
            except OSError:
                pass

    def _folder(self, scan_id: str) -> Path:
        return self._root / _safe(scan_id)

    def _path(self, scan_id: str, issue_id: str) -> Path:
        return self._folder(scan_id) / f"{_safe(issue_id)}.webp"

    def _write_file(self, scan_id: str, issue_id: str, data: bytes) -> None:
        try:
            folder = self._folder(scan_id)
            folder.mkdir(parents=True, exist_ok=True)
            self._path(scan_id, issue_id).write_bytes(data)
        except OSError:
            return

    def _read_file(self, scan_id: str, issue_id: str) -> tuple[bytes, float] | None:
        path = self._path(scan_id, issue_id)
        if not path.is_file():
            png = self._folder(scan_id) / f"{_safe(issue_id)}.png"
            path = png if png.is_file() else path
        if not path.is_file():
            return None
        try:
            return path.read_bytes(), path.stat().st_mtime
        except OSError:
            return None

    def _delete_file(self, scan_id: str, issue_id: str) -> None:
        for path in (
            self._path(scan_id, issue_id),
            self._folder(scan_id) / f"{_safe(issue_id)}.png",
        ):
            try:
                if path.exists():
                    path.unlink()
            except OSError:
                pass

    def _purge_locked(self, now: float) -> None:
        expired = [key for key, (_data, _type, created) in self._data.items() if now - created > TTL_SECONDS]
        for key in expired:
            scan_id, issue_id = key
            self._data.pop(key, None)
            self._delete_file(scan_id, issue_id)
        try:
            if not self._root.exists():
                return
            cutoff = now - TTL_SECONDS
            for folder in self._root.iterdir():
                if not folder.is_dir():
                    continue
                for path in folder.glob("*"):
                    try:
                        if path.stat().st_mtime < cutoff:
                            path.unlink()
                    except OSError:
                        pass
        except OSError:
            return
