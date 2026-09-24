"""Normalized recommendation records. No overall scores."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

RecommendationPriority = Literal["critical", "high", "medium", "low", "info"]
RecommendationImpact = Literal["high", "medium", "low"]
RecommendationEffort = Literal["small", "medium", "large"]
RecommendationStatus = Literal["open", "in_progress", "completed", "dismissed"]
RecommendationScope = Literal["site"]
AnalyzerRunStatus = Literal["completed", "failed", "missing"]


class Recommendation(BaseModel):
    id: str
    scan_id: str
    recommendation_key: str
    grouping_key: str
    scope: RecommendationScope = "site"
    scope_identifier: str = "site"
    title: str
    summary: str
    category: str
    priority: RecommendationPriority = "medium"
    effort: RecommendationEffort = "medium"
    impact: RecommendationImpact = "medium"
    status: RecommendationStatus = "open"
    affected_page_count: int = 0
    affected_element_count: int = 0
    issue_count: int = 0
    issue_ids: list[str] = Field(default_factory=list)
    issue_keys: list[str] = Field(default_factory=list)
    page_ids: list[str] = Field(default_factory=list)
    page_urls: list[str] = Field(default_factory=list)
    rationale: str = ""
    action_steps: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    depends_on_recommendation_keys: list[str] = Field(default_factory=list)
    depends_on_recommendation_ids: list[str] = Field(default_factory=list)
    source_kind: str = "issues"
    created_at: str | None = None
    updated_at: str | None = None


class RecommendationSummary(BaseModel):
    total: int = 0
    open: int = 0
    in_progress: int = 0
    completed: int = 0
    dismissed: int = 0
    high_priority: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0
    by_category: dict[str, int] = Field(default_factory=dict)
    by_priority: dict[str, int] = Field(default_factory=dict)
    by_status: dict[str, int] = Field(default_factory=dict)
    high_priority_by_category: dict[str, int] = Field(default_factory=dict)


class RecommendationsPayload(BaseModel):
    version: int = 1
    truncated: bool = False
    analyzer_status: dict[str, AnalyzerRunStatus] = Field(default_factory=dict)
    summary: RecommendationSummary = Field(default_factory=RecommendationSummary)
    recommendations: list[Recommendation] = Field(default_factory=list)
    user_status: dict[str, RecommendationStatus] = Field(default_factory=dict)
    methodology: str = ""
