"""Aggregate existing analyzer scores into a SiteLens Health Score.

Does not crawl, re-run analyzers, invent checks, or predict rankings/traffic/revenue.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from backend.errors import ScanError
from backend.scoring.coverage import build_coverage
from backend.scoring.methodology import (
    LIMITED_NOTICE,
    LIMITATIONS,
    PARTIAL_NOTICE,
    SCORE_NOTE,
    COVERAGE_NOTE,
    UNAVAILABLE_NOTICE,
    band_for,
    methodology_payload,
)
from backend.scoring.models import (
    ArchitectureNote,
    CategoryScore,
    HealthResult,
    IssueCounts,
    OverallScore,
    PageSummary,
)
from backend.scoring.normalization import (
    InvalidScoreError,
    display_contribution,
    display_score,
    extract_raw_score,
    infer_source_scale,
    normalize_score,
)
from backend.scoring.weights import (
    CALCULATION_VERSION,
    CATEGORY_HREFS,
    CATEGORY_LABELS,
    CATEGORY_WEIGHTS,
    ERROR_KEYS,
    PAYLOAD_KEYS,
    configured_total,
    validate_weights,
)

logger = logging.getLogger("sitebench.score")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _module(result: dict[str, Any], key: str) -> dict[str, Any] | None:
    payload = result.get(key)
    return payload if isinstance(payload, dict) else None


def _error_message(result: dict[str, Any], category: str) -> str | None:
    error = result.get(ERROR_KEYS[category])
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
        code = error.get("code")
        if isinstance(code, str) and code.strip():
            return code.strip()
    if error:
        return "Analyzer execution failed."
    return None


def _finding_count(payload: dict[str, Any] | None) -> int:
    if not payload:
        return 0
    checks = payload.get("checks")
    if isinstance(checks, list):
        return len(checks)
    findings = payload.get("findings")
    if isinstance(findings, list):
        return len(findings)
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    parts = [summary.get("passed"), summary.get("warnings"), summary.get("failed"), summary.get("not_applicable")]
    if any(isinstance(item, int) for item in parts):
        return sum(int(item or 0) for item in parts)
    return 0


def _page_count(payload: dict[str, Any] | None, crawled: int | None) -> int | None:
    if payload:
        summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
        for key in ("pages_analyzed", "page_count"):
            value = summary.get(key)
            if isinstance(value, int):
                return value
    return crawled


def _pages_incomplete(result: dict[str, Any]) -> bool:
    pages = _module(result, "pages")
    if not pages:
        return False
    summary = pages.get("summary") if isinstance(pages.get("summary"), dict) else {}
    if summary.get("failed") or summary.get("page_limit_reached") or summary.get("depth_limit_reached"):
        return True
    return False


def _issue_counts(issues: list[dict[str, Any]], *, source: str | None = None) -> IssueCounts:
    counts = IssueCounts()
    for item in issues:
        if source and item.get("source") != source:
            continue
        check_status = str(item.get("check_status") or "").lower()
        if check_status and check_status not in {"fail", "warning"}:
            continue
        counts.total += 1
        severity = str(item.get("severity") or "").lower()
        if severity == "critical":
            counts.critical += 1
        elif severity == "high":
            counts.high += 1
        elif severity == "medium":
            counts.medium += 1
        elif severity == "low":
            counts.low += 1
        elif severity == "info":
            counts.info += 1
    return counts


def _unified_issues(result: dict[str, Any]) -> list[dict[str, Any]]:
    payload = _module(result, "issues")
    if not payload:
        return []
    items = payload.get("issues")
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _crawled_pages(result: dict[str, Any]) -> int | None:
    pages = _module(result, "pages")
    if not pages:
        return None
    summary = pages.get("summary") if isinstance(pages.get("summary"), dict) else {}
    crawled = summary.get("crawled")
    return crawled if isinstance(crawled, int) else None


def _page_summary(result: dict[str, Any]) -> PageSummary:
    pages = _module(result, "pages")
    if not pages:
        return PageSummary()
    items = pages.get("items") if isinstance(pages.get("items"), list) else []
    crawled = [item for item in items if isinstance(item, dict) and item.get("crawl_status") == "crawled"]
    if not crawled:
        summary = pages.get("summary") if isinstance(pages.get("summary"), dict) else {}
        analyzed = summary.get("crawled") if isinstance(summary.get("crawled"), int) else None
        return PageSummary(pages_analyzed=analyzed)
    with_issues = sum(1 for item in crawled if int(item.get("issue_count") or 0) > 0)
    return PageSummary(
        pages_analyzed=len(crawled),
        pages_with_issues=with_issues,
        pages_without_issues=len(crawled) - with_issues,
    )


def _category_row(
    result: dict[str, Any],
    category: str,
    *,
    weights: dict[str, float],
    crawled: int | None,
    issues: list[dict[str, Any]],
    pages_incomplete: bool,
) -> CategoryScore:
    payload = _module(result, PAYLOAD_KEYS[category])
    error = _error_message(result, category)
    issue_summary = _issue_counts(issues, source=category)
    base = dict(
        category=category,
        name=CATEGORY_LABELS[category],
        weight=float(weights[category]),
        href=CATEGORY_HREFS[category],
        finding_count=_finding_count(payload),
        issue_count=issue_summary.total,
        issue_summary=issue_summary,
        page_count=_page_count(payload, crawled),
    )
    if payload is None:
        status = "failed" if error else "unavailable"
        return CategoryScore(
            **base,
            score=None,
            raw_score=None,
            available=False,
            status=status,
            reason=error or "Analyzer did not produce a usable score.",
        )
    raw = extract_raw_score(payload)
    try:
        normalized = normalize_score(raw, infer_source_scale(payload))
    except InvalidScoreError as exc:
        return CategoryScore(
            **base,
            score=None,
            raw_score=float(raw) if isinstance(raw, (int, float)) and not isinstance(raw, bool) else None,
            normalized_score=None,
            available=False,
            status="failed",
            reason=str(exc),
        )
    if not normalized["available"]:
        return CategoryScore(
            **base,
            score=None,
            raw_score=None,
            normalized_score=None,
            available=False,
            status="failed" if error else "unavailable",
            reason=error or "Analyzer did not produce a usable score.",
        )
    status = "partial" if error or pages_incomplete else "available"
    return CategoryScore(
        **base,
        score=display_score(normalized["score"]),
        raw_score=normalized["raw"],
        normalized_score=float(normalized["score"]),
        available=True,
        status=status,
        reason=error,
    )


def calculate_health(
    result: dict[str, Any] | None,
    *,
    weights: dict[str, float] | None = None,
    calculated_at: str | None = None,
) -> HealthResult:
    payload = result or {}
    configured = validate_weights(weights)
    crawled = _crawled_pages(payload)
    issues = _unified_issues(payload)
    incomplete = _pages_incomplete(payload)
    categories = [
        _category_row(payload, key, weights=configured, crawled=crawled, issues=issues, pages_incomplete=incomplete)
        for key in configured
    ]
    usable = [item for item in categories if item.available and item.normalized_score is not None]
    available_weight = sum(item.weight for item in usable)
    configured_weight = configured_total(configured)
    coverage = build_coverage(
        configured_weight=configured_weight,
        available_weight=available_weight,
        configured_categories=len(configured),
        available_categories=len(usable),
    )

    overall_value: float | None = None
    if usable and available_weight > 0:
        overall_value = sum(float(item.normalized_score) * item.weight for item in usable) / available_weight

    for item in categories:
        if item.available and item.normalized_score is not None and available_weight > 0:
            item.effective_weight = display_contribution((item.weight / available_weight) * 100.0)
            item.weighted_contribution = display_contribution((float(item.normalized_score) * item.weight) / available_weight)
        else:
            item.effective_weight = None
            item.weighted_contribution = None

    displayed = display_score(overall_value)
    band = band_for(displayed)
    overall_status = band if displayed is not None else UNAVAILABLE_NOTICE
    notice = None
    if displayed is None:
        notice = "SiteLens could not calculate the score from the available analysis results."
    elif coverage.status == "limited" or coverage.status == "unavailable":
        notice = LIMITED_NOTICE
    elif coverage.status == "partial":
        notice = PARTIAL_NOTICE

    logger.info(
        "scoring_completed version=%s available=%s unavailable=%s coverage=%s score=%s",
        CALCULATION_VERSION,
        [item.category for item in usable],
        [item.category for item in categories if not item.available],
        coverage.coverage_percent,
        displayed,
    )

    return HealthResult(
        calculation_version=CALCULATION_VERSION,
        calculated_at=calculated_at or _now(),
        overall=OverallScore(
            score=displayed,
            status=overall_status,
            band=band,
            coverage_percent=coverage.coverage_percent,
            coverage_status=coverage.status,
            available_categories=len(usable),
            configured_categories=len(configured),
        ),
        coverage=coverage,
        categories=categories,
        architecture=ArchitectureNote(),
        issue_summary=_issue_counts(issues),
        page_summary=_page_summary(payload),
        methodology=methodology_payload(configured),
        limitations=list(LIMITATIONS),
        score_note=SCORE_NOTE,
        coverage_note=COVERAGE_NOTE,
        partial_notice=notice,
    )


def score_scan_result(result: dict[str, Any] | None) -> HealthResult:
    logger.info("scoring_started version=%s", CALCULATION_VERSION)
    if not result:
        raise ScanError("SCORE_FAILED", "Health score unavailable.")
    health = calculate_health(result)
    if health.overall.score is None and health.coverage.available_categories == 0:
        logger.info("scoring_unavailable version=%s", CALCULATION_VERSION)
    return health
