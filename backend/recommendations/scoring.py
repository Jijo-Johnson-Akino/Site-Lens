"""Deterministic priority, impact, and effort. No overall recommendation score."""

from __future__ import annotations

from typing import Any

from backend.recommendations.config import (
    HIGH_ELEMENT_IMPACT,
    HIGH_PAGE_IMPACT,
    MEDIUM_ELEMENT_IMPACT,
    MEDIUM_PAGE_IMPACT,
)

PRIORITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
IMPACT_RANK = {"high": 3, "medium": 2, "low": 1}
EFFORT_RANK = {"large": 3, "medium": 2, "small": 1}
STATUS_RANK = {"open": 3, "in_progress": 2, "completed": 1, "dismissed": 0}

_PRIORITY_BY_RANK = {rank: label for label, rank in PRIORITY_RANK.items()}
_IMPACT_BY_RANK = {rank: label for label, rank in IMPACT_RANK.items()}


def highest_priority(values: list[str], *, cap: str | None = None) -> str:
    rank = 0
    for value in values:
        rank = max(rank, PRIORITY_RANK.get(value, 0))
    label = _PRIORITY_BY_RANK.get(rank, "info")
    if cap and PRIORITY_RANK.get(label, 0) > PRIORITY_RANK.get(cap, 4):
        return cap
    return label


def calculate_priority(issues: list[Any], *, cap: str | None = None, fallback: str = "medium") -> str:
    if not issues:
        return highest_priority([fallback], cap=cap)
    values = [getattr(item, "priority", None) or fallback for item in issues]
    return highest_priority(values, cap=cap)


def calculate_impact(
    *,
    base: str,
    priority: str,
    page_count: int,
    element_count: int,
) -> str:
    rank = IMPACT_RANK.get(base, 2)
    if page_count >= HIGH_PAGE_IMPACT or element_count >= HIGH_ELEMENT_IMPACT:
        rank = max(rank, 3)
    elif page_count >= MEDIUM_PAGE_IMPACT or element_count >= MEDIUM_ELEMENT_IMPACT:
        rank = max(rank, 2)
    if priority == "critical":
        rank = max(rank, 3)
    elif priority == "high":
        rank = max(rank, 2)
    elif priority == "info":
        rank = min(rank, 1)
    return _IMPACT_BY_RANK.get(rank, "medium")


def calculate_effort(base: str) -> str:
    return base if base in EFFORT_RANK else "medium"
