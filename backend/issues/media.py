"""Classify issues for screenshots vs snippets. Never invent visual evidence."""

from __future__ import annotations

import re
from typing import Any, Literal

from backend.issues.models import UnifiedIssue

VisualKind = Literal["screenshot", "snippet", "none"]
ViewportType = Literal["desktop", "mobile"]

SCREENSHOT_IDS = {
    "A11Y-CONTRAST-001",
    "A11Y-IMG-001",
    "A11Y-IMG-003",
    "A11Y-IMG-004",
    "A11Y-HEAD-003",
    "A11Y-HEAD-004",
    "SEO-IMG-001",
    "SEO-H1-002",
    "SEO-HEAD-001",
    "PERF-VITAL-002",
    "MOBILE-OVERFLOW-001",
    "MOBILE-OVERFLOW-002",
    "MOBILE-TOUCH-001",
    "MOBILE-TOUCH-002",
    "MOBILE-TOUCH-003",
    "MOBILE-LAYOUT-001",
    "MOBILE-LAYOUT-002",
    "MOBILE-LAYOUT-003",
    "MOBILE-LAYOUT-004",
    "MOBILE-IMG-002",
    "MOBILE-CTA-001",
    "MOBILE-CTA-002",
    "UX-LAYOUT-001",
    "UX-LAYOUT-002",
    "UX-LAYOUT-003",
}

SCREENSHOT_PREFIXES = (
    "A11Y-CONTRAST",
    "MOBILE-OVERFLOW",
    "MOBILE-TOUCH",
    "MOBILE-LAYOUT",
    "MOBILE-CTA",
)

SNIPPET_IDS = {
    "SEO-TITLE-001",
    "SEO-TITLE-002",
    "SEO-TITLE-003",
    "SEO-TITLE-004",
    "SEO-META-001",
    "SEO-META-002",
    "SEO-META-003",
    "SEO-META-004",
    "SEO-CAN-001",
    "SEO-CAN-002",
    "SEO-CAN-003",
    "SEO-ROBOTS-001",
    "SEO-ROBOTS-002",
    "SEO-ROBOTS-003",
    "SEO-SITEMAP-001",
    "SEO-SITEMAP-002",
    "SEO-SITEMAP-003",
    "SEO-LINK-003",
    "A11Y-DOC-002",
    "SCHEMA-PRESENCE-001",
    "SCHEMA-REQUIRED-001",
}

SNIPPET_PREFIXES = ("SEO-TITLE", "SEO-META", "SEO-CAN", "SEO-ROBOTS", "SEO-SITEMAP", "SCHEMA-")

FALLBACK_SELECTORS: dict[str, str] = {
    "A11Y-IMG-001": "img:not([alt])",
    "A11Y-IMG-003": "input[type='image']",
    "A11Y-IMG-004": "a img, button img",
    "SEO-IMG-001": "img:not([alt])",
    "A11Y-HEAD-003": "h1, h2, h3, h4, h5, h6",
    "A11Y-HEAD-004": "h1",
    "SEO-H1-002": "h1",
    "SEO-HEAD-001": "h1, h2, h3",
}

_BADGE = ("①", "②", "③")


def visual_kind_for(check_id: str | None) -> VisualKind:
    raw = (check_id or "").strip().upper()
    if not raw:
        return "none"
    if raw in SCREENSHOT_IDS or raw.startswith(SCREENSHOT_PREFIXES):
        return "screenshot"
    if raw in SNIPPET_IDS or raw.startswith(SNIPPET_PREFIXES):
        return "snippet"
    lowered = (check_id or "").lower()
    if "broken" in lowered and "link" in lowered:
        return "snippet"
    return "none"


def viewport_type_for(issue: UnifiedIssue) -> ViewportType:
    blob = " ".join(
        str(part or "")
        for part in (issue.viewport, issue.check_id, issue.source, issue.category)
    ).lower()
    if "mobile" in blob or "390" in blob or "375" in blob:
        return "mobile"
    return "desktop"


def collect_selectors(issue: UnifiedIssue) -> list[str]:
    found: list[str] = []

    def add(value: str | None) -> None:
        text = (value or "").strip()
        if text and text not in found:
            found.append(text)

    add(issue.selector)
    add(issue.highlighted_selector)
    for occurrence in issue.occurrences:
        add(occurrence.selector)
        for element in occurrence.affected_elements:
            add(element.selector)
    evidence = issue.evidence or {}
    for key in ("selector", "selectors"):
        raw = evidence.get(key)
        if isinstance(raw, str):
            add(raw)
        elif isinstance(raw, list):
            for item in raw[:6]:
                if isinstance(item, str):
                    add(item)
                elif isinstance(item, dict):
                    add(item.get("selector"))
    details = issue.details or {}
    sources = details.get("cls_sources") or evidence.get("cls_sources")
    if isinstance(sources, list):
        for item in sources[:6]:
            if isinstance(item, dict):
                add(item.get("selector"))
    fallback = FALLBACK_SELECTORS.get((issue.check_id or "").upper())
    if not found and fallback:
        add(fallback)
    return found[:8]


def caption_for(issue: UnifiedIssue, selectors: list[str], extra_count: int = 0) -> str:
    check = (issue.check_id or "").upper()
    evidence = issue.evidence or {}
    detected = evidence.get("detected") or issue.details.get("detected") if issue.details else None
    first = selectors[0] if selectors else issue.highlighted_selector
    more = extra_count
    suffix = f" +{more} more" if more > 0 else ""
    if check.startswith("A11Y-CONTRAST"):
        ratio = _contrast_ratio(issue)
        needed = "4.5:1"
        if ratio:
            return f"Highlighted: low-contrast text ({ratio} vs {needed} needed){suffix}"
        return f"Highlighted: text with insufficient color contrast{suffix}"
    if "TOUCH" in check or "CTA" in check:
        measured = evidence.get("measured_value") or (issue.details or {}).get("measured_value")
        expected = evidence.get("expected_value") or (issue.details or {}).get("expected_value") or 44
        if measured is not None:
            return f"Highlighted: tap target ({_px(measured)} vs {_px(expected)} minimum){suffix}"
        return f"Highlighted: tap target below {_px(expected)}{suffix}"
    if check in {"A11Y-IMG-001", "A11Y-IMG-003", "A11Y-IMG-004", "SEO-IMG-001"}:
        return f"Highlighted: image missing alt text{suffix}"
    if "OVERFLOW" in check or "LAYOUT" in check:
        return f"Highlighted: layout or overflow on this viewport{suffix}"
    if "HEAD" in check or "H1" in check:
        return f"Highlighted: heading structure{suffix}"
    if check == "PERF-VITAL-002":
        return f"Highlighted: layout-shift region{suffix}"
    if first:
        label = first if len(first) < 64 else first[:61] + "…"
        if detected:
            return f"Highlighted: {label} ({detected}){suffix}"
        return f"Highlighted: {label}{suffix}"
    return issue.title


def _px(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return f"{int(number)}px"
    return f"{number:.0f}px"


def _contrast_ratio(issue: UnifiedIssue) -> str | None:
    blob = " ".join(
        [
            issue.description or "",
            issue.title or "",
            str((issue.evidence or {}).get("detected") or ""),
            str((issue.details or {}).get("detected") or ""),
        ]
    )
    match = re.search(r"(\d+(?:\.\d+)?)\s*:\s*1", blob)
    if match:
        return f"{match.group(1)}:1"
    return None


def attach_snippets(issues: list[UnifiedIssue], result: dict[str, Any] | None) -> None:
    payload = result or {}
    html = payload.get("html") if isinstance(payload.get("html"), dict) else {}
    website = payload.get("website") if isinstance(payload.get("website"), dict) else {}
    http = payload.get("http") if isinstance(payload.get("http"), dict) else {}
    robots = payload.get("robots_txt") if isinstance(payload.get("robots_txt"), dict) else {}
    sitemap = payload.get("sitemap") if isinstance(payload.get("sitemap"), dict) else {}
    for issue in issues:
        kind = visual_kind_for(issue.check_id)
        issue.details = dict(issue.details or {})
        issue.details["visual_kind"] = kind
        if kind != "snippet":
            continue
        code, language, highlight = build_snippet(issue, html=html, website=website, http=http, robots=robots, sitemap=sitemap)
        if not code:
            continue
        issue.snippet = code
        issue.snippet_language = language
        issue.snippet_highlight_line = highlight


def build_snippet(
    issue: UnifiedIssue,
    *,
    html: dict[str, Any],
    website: dict[str, Any],
    http: dict[str, Any],
    robots: dict[str, Any],
    sitemap: dict[str, Any],
) -> tuple[str | None, str, int | None]:
    check = (issue.check_id or "").upper()
    title = html.get("title")
    meta = html.get("meta_description")
    canonical = html.get("canonical")
    if check.startswith("SEO-TITLE") or check == "A11Y-DOC-002":
        if title:
            return f"<title>{_clip(title, 180)}</title>", "html", 1
        return "<head>\n  <!-- <title> is missing on this page -->\n</head>", "html", 2
    if check.startswith("SEO-META"):
        if meta:
            return f'<meta name="description" content="{_clip(meta, 220)}">', "html", 1
        return '<head>\n  <!-- <meta name="description"> is missing -->\n</head>', "html", 2
    if check.startswith("SEO-CAN"):
        if canonical:
            return f'<link rel="canonical" href="{_clip(str(canonical), 220)}">', "html", 1
        return '<head>\n  <!-- rel="canonical" is missing -->\n</head>', "html", 2
    if check.startswith("SEO-ROBOTS"):
        status = robots.get("status_code")
        exists = robots.get("exists")
        line = f"GET /robots.txt → {status if status is not None else ('found' if exists else 'not found')}"
        return line, "http", 1
    if check.startswith("SEO-SITEMAP"):
        status = sitemap.get("status_code")
        exists = sitemap.get("exists")
        line = f"GET /sitemap.xml → {status if status is not None else ('found' if exists else 'not found')}"
        return line, "http", 1
    if check.startswith("SCHEMA"):
        detected = (issue.evidence or {}).get("detected")
        if detected:
            return str(detected)[:800], "json", 1
        return "<!-- No structured data (JSON-LD / microdata) was detected on this page -->", "html", 1
    if check == "SEO-LINK-003" or "broken" in (issue.check_id or "").lower():
        return _link_snippet(issue), "html", 1
    detected = (issue.evidence or {}).get("detected")
    if isinstance(detected, str) and detected.strip():
        return _clip(detected, 600), "text", 1
    return None, "text", None


def _link_snippet(issue: UnifiedIssue) -> str:
    evidence = issue.evidence or {}
    href = evidence.get("href") or evidence.get("url") or issue.resource_url
    text = evidence.get("text") or evidence.get("link_text")
    status = evidence.get("status_code") or evidence.get("status")
    parts = ["<a"]
    if href:
        parts.append(f' href="{_clip(str(href), 180)}"')
    parts.append(">")
    parts.append(_clip(str(text or "link"), 80))
    parts.append("</a>")
    if status is not None:
        parts.append(f"\n<!-- HTTP {status} -->")
    return "".join(parts)


def _clip(value: str, limit: int) -> str:
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def screenshot_summary_note(captured: int, visual: int) -> str:
    return f"Screenshots captured for {captured} of {visual} visual issues."
