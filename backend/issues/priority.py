"""Deterministic issue priority. Priority is not the same as severity.

Formula (documented, configurable, no AI):

    priority_score =
        severity_weight
        + status_weight
        + min(15, affected_element_count * 2)
        + min(15, max(0, affected_page_count - 1) * 5)
        + (10 if the finding affects the primary scanned page)
        + (5 if evidence is present)
        + (10 if the finding is a blocking functional/accessibility issue)

Then:

    80–100 → critical
    60–79  → high
    35–59  → medium
    0–34   → low

Caps (do not over-prioritize):
    - social / optional metadata → max 34 (low)
    - status info → max 34 (low)
    - status not_applicable → 0 (low)
    - score is never increased above source severity by more than one band
      except for blocking accessibility/mobile overflow failures
"""

from __future__ import annotations

from typing import Any

SEVERITY_WEIGHT = {
    "critical": 40,
    "high": 28,
    "medium": 16,
    "low": 8,
    "info": 2,
}

STATUS_WEIGHT = {
    "fail": 20,
    "warning": 10,
    "info": 4,
    "pass": 0,
    "not_applicable": 0,
}

PRIORITY_BANDS = (
    (80, "critical"),
    (60, "high"),
    (35, "medium"),
    (0, "low"),
)

SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
PRIORITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}

SOCIAL_KEYS = {
    "seo.social.001",
    "seo.social.002",
    "seo.social.003",
    "seo.social.004",
}

BLOCKING_KEYS = {
    "mobile.horizontal_overflow",
    "accessibility.form.label.missing",
    "accessibility.button.name.missing",
}

BLOCKING_GROUPS = {"keyboard", "controls", "forms"}
BLOCKING_CHECK_PREFIXES = ("A11Y-KEY-", "A11Y-FOCUS-", "SEO-INDEX-")


def _band_for_score(score: int) -> str:
    for threshold, label in PRIORITY_BANDS:
        if score >= threshold:
            return label
    return "low"


def _is_social(finding: dict[str, Any]) -> bool:
    if finding.get("issue_key") in SOCIAL_KEYS:
        return True
    group = str(finding.get("group") or finding.get("subcategory") or "").lower()
    return group in {"social"}


def _is_blocking(finding: dict[str, Any]) -> bool:
    if finding.get("status") != "fail":
        return False
    if finding.get("issue_key") in BLOCKING_KEYS:
        return True
    group = str(finding.get("group") or "").lower()
    if finding.get("source") == "accessibility" and group in BLOCKING_GROUPS:
        return True
    check_id = str(finding.get("check_id") or "")
    return any(check_id.startswith(prefix) for prefix in BLOCKING_CHECK_PREFIXES)


def _cap_priority(priority: str, severity: str, *, blocking: bool) -> str:
    """Do not jump more than one band above source severity unless blocking."""
    if blocking:
        return priority
    max_rank = min(4, SEVERITY_RANK.get(severity, 2) + 1)
    if PRIORITY_RANK.get(priority, 1) > max_rank:
        for label, rank in PRIORITY_RANK.items():
            if rank == max_rank:
                return label
    return priority


def calculate_priority(
    finding: dict[str, Any],
    *,
    affected_page_count: int = 1,
    affected_element_count: int | None = None,
    primary_page: str | None = None,
) -> tuple[int, str]:
    """Return ``(priority_score, priority_label)`` for a finding or grouped issue."""
    status = finding.get("status") or finding.get("check_status") or "fail"
    severity = finding.get("severity") or "medium"
    elements = finding.get("affected_element_count") if affected_element_count is None else affected_element_count
    try:
        elements = int(elements or 0)
    except (TypeError, ValueError):
        elements = 0
    try:
        pages = int(affected_page_count or 1)
    except (TypeError, ValueError):
        pages = 1
    if pages < 1:
        pages = 1

    if status == "not_applicable":
        return 0, "low"

    score = SEVERITY_WEIGHT.get(severity, 16) + STATUS_WEIGHT.get(status, 0)
    score += min(15, max(0, elements) * 2)
    score += min(15, max(0, pages - 1) * 5)

    page_url = finding.get("page_url") or ""
    pages_list = finding.get("pages") or []
    affects_primary = False
    if primary_page:
        if page_url == primary_page or primary_page in pages_list:
            affects_primary = True
        elif not page_url and pages == 1:
            affects_primary = True
    if affects_primary:
        score += 10

    evidence = finding.get("evidence") or {}
    if evidence:
        score += 5

    blocking = _is_blocking(finding)
    if blocking:
        score += 10

    score = max(0, min(100, int(score)))

    if status == "info" or _is_social(finding):
        score = min(score, 34)

    label = _band_for_score(score)
    label = _cap_priority(label, severity, blocking=blocking)
    return score, label
