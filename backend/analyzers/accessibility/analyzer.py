from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from backend.analyzers.accessibility.axe_runner import axe_to_checks, run_axe
from backend.analyzers.accessibility.checks import CHECK_RUNNERS
from backend.analyzers.accessibility.config import (
    AXE_TAGS,
    DEFAULT_SCORING,
    KEYBOARD_TAB_LIMIT,
    LIMITATIONS,
    A11yScoringConfig,
)
from backend.analyzers.accessibility.models import (
    A11yCategoryScore,
    A11yPageInfo,
    A11yResult,
    A11yStandard,
    A11yTool,
    AccessibleSnapshot,
    CheckResult,
)
from backend.analyzers.accessibility.scoring import (
    CATEGORY_LABELS,
    apply_weights,
    category_scores,
    collect_issues,
    merge_findings,
    narrative_summary,
    overall_score,
    severity_counts,
    summarize,
)
from backend.analyzers.accessibility.snapshots import COLLECT_JS, normalize_snapshot
from backend.analyzers.uiux.browser import UIUXBrowser
from backend.errors import ScanError
from backend.services.url_validator import UrlValidator

ProgressFn = Callable[[int, str], Awaitable[None] | None]

ACTIVE_SEL_JS = """() => {
  const el = document.activeElement;
  if (!el || el === document.body || el === document.documentElement) return null;
  const tag = (el.tagName || "div").toLowerCase();
  let id = "";
  if (el.id && /^[A-Za-z][\\w-]{0,40}$/.test(el.id)) id = "#" + el.id;
  return (tag + id).slice(0, 72);
}"""


def collect_dom_checks(snapshot: AccessibleSnapshot) -> list[CheckResult]:
    checks: list[CheckResult] = []
    for runner in CHECK_RUNNERS:
        checks.extend(runner(snapshot))
    return checks


def analyze_snapshot(
    snapshot: AccessibleSnapshot,
    axe: dict[str, Any] | None = None,
    *,
    screenshots: list[dict] | None = None,
    config: A11yScoringConfig | None = None,
) -> A11yResult:
    scoring = config or DEFAULT_SCORING
    page_url = str(snapshot.page.get("final_url") or snapshot.page.get("url") or "")
    dom_checks = collect_dom_checks(snapshot)
    axe_checks = axe_to_checks(axe or {}, page_url)
    checks = apply_weights(merge_findings(dom_checks, axe_checks), scoring)
    categories = category_scores(checks, scoring)
    score = overall_score(checks, scoring)
    cards = [
        A11yCategoryScore(
            id=group,
            name=CATEGORY_LABELS.get(group, group),
            score=categories.get(group),
            finding_count=sum(1 for check in checks if check.group == group and check.status in {"fail", "warning"}),
        )
        for group in scoring.category_weights
    ]
    return A11yResult(
        score=score,
        summary=summarize(checks),
        narrative=narrative_summary(score, checks),
        categories=categories,
        category_cards=cards,
        checks=checks,
        findings=checks,
        issues=collect_issues(checks),
        page=A11yPageInfo(analyzed_url=str(snapshot.page.get("url") or page_url), final_url=page_url),
        tool=A11yTool(
            name="axe-core",
            version=(axe or {}).get("version"),
            automated=True,
            tags=list(AXE_TAGS),
            axe_violations=len((axe or {}).get("violations") or []),
            axe_incomplete=len((axe or {}).get("incomplete") or []),
            axe_passes=len((axe or {}).get("passes") or []),
            axe_inapplicable=len((axe or {}).get("inapplicable") or []),
        ),
        standard=A11yStandard(),
        limitations=list(LIMITATIONS),
        screenshots=screenshots or [],
        severity_counts=severity_counts(checks),
    )


def _probe_tabs(page: Any, focusable: int) -> list[str]:
    path: list[str] = []
    limit = min(KEYBOARD_TAB_LIMIT, focusable if focusable > 0 else KEYBOARD_TAB_LIMIT)
    try:
        for _ in range(limit):
            page.keyboard.press("Tab")
            selector = page.evaluate(ACTIVE_SEL_JS)
            if selector:
                path.append(str(selector))
    except Exception:
        return path
    return path


def _inspect_page(page: Any, final_url: str, requested_url: str) -> tuple[AccessibleSnapshot, dict[str, Any]]:
    axe = run_axe(page)
    raw = page.evaluate(COLLECT_JS)
    snapshot = normalize_snapshot(raw or {}, url=requested_url, final_url=final_url)
    tab_path = _probe_tabs(page, int((snapshot.focus or {}).get("focusable_count") or 0))
    snapshot.focus = {**(snapshot.focus or {}), "tab_path": tab_path}
    return snapshot, axe


class PlaywrightA11yAnalyzer:
    def __init__(self, validator: UrlValidator | None = None, scoring: A11yScoringConfig | None = None) -> None:
        self._validator = validator or UrlValidator()
        self._scoring = scoring or DEFAULT_SCORING

    async def analyze(
        self,
        *,
        url: str,
        scan_id: str | None = None,
        screenshots: list[dict] | None = None,
        on_progress: ProgressFn | None = None,
    ) -> A11yResult:
        await _emit(on_progress, 92, "Accessibility analysis")
        try:
            snapshot, axe = await asyncio.to_thread(self._analyze_sync, url)
        except ScanError as exc:
            if exc.code in {"WEBSITE_UNREACHABLE", "RENDER_FAILED"}:
                raise ScanError("A11Y_FAILED", "The website could not be rendered for accessibility analysis.") from exc
            raise
        return analyze_snapshot(snapshot, axe, screenshots=screenshots, config=self._scoring)

    def analyze_html(self, html: str, page_url: str = "https://example.com/") -> A11yResult:
        with UIUXBrowser(self._validator) as browser:
            snapshot, axe = browser.inspect(
                lambda page, final_url: _inspect_page(page, final_url, page_url),
                html=html,
                viewport_name="desktop",
                page_url=page_url,
            )
        return analyze_snapshot(snapshot, axe, config=self._scoring)

    def _analyze_sync(self, url: str) -> tuple[AccessibleSnapshot, dict[str, Any]]:
        with UIUXBrowser(self._validator) as browser:
            return browser.inspect(
                lambda page, final_url: _inspect_page(page, final_url, url),
                url=url,
                viewport_name="desktop",
            )


async def _emit(on_progress: ProgressFn | None, progress: int, step: str) -> None:
    if on_progress is None:
        return
    maybe = on_progress(progress, step)
    if maybe is not None:
        await maybe
