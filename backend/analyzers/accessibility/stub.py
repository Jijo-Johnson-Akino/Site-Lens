"""Deterministic accessibility results for API tests that must not launch Chromium."""

from __future__ import annotations

from backend.analyzers.accessibility.analyzer import ProgressFn, analyze_snapshot
from backend.analyzers.accessibility.models import A11yResult, AccessibleSnapshot


def accessible_snapshot(url: str = "https://example.com/") -> AccessibleSnapshot:
    return AccessibleSnapshot.model_validate(
        {
            "page": {"url": url, "final_url": url, "ready_state": "complete"},
            "document": {"lang": "en", "dir": "ltr", "title": "Example", "lang_present": True},
            "landmarks": {"main": 1, "nav": 1, "header": 1, "footer": 0, "unnamed_navs": 0, "empty": []},
            "headings": [{"level": 1, "selector": "h1", "text": "Home", "empty": False, "hidden": False}],
            "images": [{"selector": "img", "alt": "Chart", "has_alt": True, "in_link": False, "visible": True}],
            "links": [{"selector": "a", "href": "/a", "name": "About", "named": True, "visible": True}],
            "controls": [{"selector": "button", "name": "Get Started", "named": True, "disabled": False, "visible": True}],
            "fields": [{"selector": "input#email", "named": True, "required": False, "type": "email"}],
            "forms": [{"selector": "form", "has_submit": True, "submit_named": True, "fieldsets": 0}],
            "radio_groups": 0,
            "radio_groups_without_fieldset": 0,
            "aria": {"broken_refs": [], "hidden_focusable": []},
            "ids": {"duplicates": []},
            "tables": [],
            "iframes": [],
            "dialogs": [],
            "media": [],
            "focus": {"tabindex_positive": [], "hidden_focusable": [], "focusable_count": 3, "tab_path": ["a", "button", "input#email"]},
            "viewport_meta": {"content": "width=device-width, initial-scale=1", "present": True},
            "skip": {"exists": True, "selector": "a.skip"},
            "live": [],
        }
    )


class StubA11yAnalyzer:
    async def analyze(self, *, url: str, scan_id: str | None = None, screenshots=None, on_progress: ProgressFn | None = None) -> A11yResult:
        if on_progress:
            maybe = on_progress(92, "Accessibility analysis")
            if maybe is not None:
                await maybe
        return analyze_snapshot(accessible_snapshot(url), {"version": "stub", "violations": [], "incomplete": [], "passes": [], "inapplicable": []}, screenshots=screenshots)
