"""Competitor benchmark records. Independent scans, no copied metrics."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

CompetitorStatus = Literal["queued", "scanning", "completed", "failed", "cancelled"]


class CompetitorBenchmark(BaseModel):
    id: str
    scan_id: str
    name: str
    url: str
    normalized_url: str
    competitor_scan_id: str
    status: CompetitorStatus = "queued"
    created_at: str | None = None
    updated_at: str | None = None


class CompetitorListPayload(BaseModel):
    version: int = 1
    items: list[CompetitorBenchmark] = Field(default_factory=list)
