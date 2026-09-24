from __future__ import annotations


class ScanError(Exception):
    """Safe, user-facing scan failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
