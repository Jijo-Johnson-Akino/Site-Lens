from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ScanStatus = Literal["queued", "running", "completed", "failed", "cancelled"]


class ScanRecord(BaseModel):
    id: str
    url: str
    normalized_url: str
    status: ScanStatus
    progress: int = 0
    current_step: str = "Validating website"
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: dict[str, str] | None = None
    result: dict[str, Any] | None = None


class ScanCreateRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


class ScanCreateResponse(BaseModel):
    scan_id: str
    status: ScanStatus


class ScanStatusResponse(BaseModel):
    scan_id: str
    url: str
    normalized_url: str
    status: ScanStatus
    progress: int
    current_step: str
    created_at: str | None = None
    completed_at: str | None = None
    error: dict[str, str] | None = None
    result: dict[str, Any] | None = None


class ApiError(BaseModel):
    code: str
    message: str


class ApiErrorResponse(BaseModel):
    error: ApiError
