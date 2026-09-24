from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CategoryStatus = Literal["available", "partial", "unavailable", "failed"]
CoverageStatus = Literal["complete", "partial", "limited", "unavailable"]


class IssueCounts(BaseModel):
    total: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0


class CategoryScore(BaseModel):
    category: str
    name: str
    score: int | None = None
    raw_score: float | None = None
    normalized_score: float | None = Field(default=None, exclude=True)
    weight: float
    effective_weight: float | None = None
    weighted_contribution: float | None = None
    available: bool
    status: CategoryStatus
    href: str
    finding_count: int = 0
    issue_count: int = 0
    issue_summary: IssueCounts = Field(default_factory=IssueCounts)
    page_count: int | None = None
    reason: str | None = None


class ScoreCoverage(BaseModel):
    configured_weight: float
    available_weight: float
    coverage_percent: float | None
    status: CoverageStatus
    available_categories: int
    configured_categories: int
    explanation: str


class OverallScore(BaseModel):
    score: int | None
    status: str
    band: str | None = None
    coverage_percent: float | None = None
    coverage_status: CoverageStatus
    available_categories: int
    configured_categories: int


class PageSummary(BaseModel):
    pages_analyzed: int | None = None
    pages_with_issues: int | None = None
    pages_without_issues: int | None = None


class ArchitectureNote(BaseModel):
    name: str = "Website Architecture"
    status: str = "informational"
    included_in_score: bool = False
    href: str = "architecture"
    note: str = "Website Architecture is a structural crawl visualization and is not included in the weighted Health Score."


class ScoreMethodology(BaseModel):
    calculation_version: str
    weights: dict[str, float]
    formula: str
    score_range: list[int] = Field(default_factory=lambda: [0, 100])
    unavailable_behavior: str
    rounding: str
    bands: dict[str, str]
    coverage_rules: dict[str, str]


class HealthResult(BaseModel):
    calculation_version: str
    calculated_at: str
    overall: OverallScore
    coverage: ScoreCoverage
    categories: list[CategoryScore] = Field(default_factory=list)
    architecture: ArchitectureNote = Field(default_factory=ArchitectureNote)
    issue_summary: IssueCounts = Field(default_factory=IssueCounts)
    page_summary: PageSummary = Field(default_factory=PageSummary)
    methodology: ScoreMethodology
    limitations: list[str] = Field(default_factory=list)
    score_note: str
    coverage_note: str
    partial_notice: str | None = None
