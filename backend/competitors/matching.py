"""Suggested page matches. Deterministic signals only — never claimed as equivalent pages."""

from __future__ import annotations

from typing import Any

from backend.pages.models import PageRecord
from backend.services.url_identity import url_path


def _title_tokens(title: str | None) -> set[str]:
    text = (title or "").lower()
    return {part for part in "".join(ch if ch.isalnum() else " " for ch in text).split() if len(part) > 2}


def score_match(primary: PageRecord, candidate: PageRecord) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    primary_type = (primary.page_type or "").lower()
    candidate_type = (candidate.page_type or "").lower()
    if primary_type and primary_type == candidate_type:
        score += 3
        reasons.append("same page type")
    primary_path = url_path(primary.normalized_url or primary.url)
    candidate_path = url_path(candidate.normalized_url or candidate.url)
    if primary_path and primary_path == candidate_path:
        score += 3
        reasons.append("similar URL path")
    elif primary_path not in {"", "/"} and candidate_path.rstrip("/") == primary_path.rstrip("/"):
        score += 2
        reasons.append("similar URL path")
    left = _title_tokens(primary.title)
    right = _title_tokens(candidate.title)
    if left and right and left & right:
        score += 1
        reasons.append("similar title text")
    return score, reasons


def suggest_matches(primary: PageRecord, candidates: list[PageRecord], *, limit: int = 5) -> list[dict[str, Any]]:
    ranked: list[tuple[int, PageRecord, list[str]]] = []
    for candidate in candidates:
        if candidate.crawl_status not in {"crawled", "failed", "skipped"}:
            continue
        score, reasons = score_match(primary, candidate)
        if score <= 0:
            continue
        ranked.append((score, candidate, reasons))
    ranked.sort(key=lambda item: (-item[0], item[1].normalized_url or item[1].url))
    rows = []
    for score, page, reasons in ranked[:limit]:
        rows.append(
            {
                "page_id": page.id,
                "url": page.url,
                "title": page.title,
                "page_type": page.page_type,
                "label": "Suggested match",
                "reasons": reasons,
                "score": score,
            }
        )
    return rows
