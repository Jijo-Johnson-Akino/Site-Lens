from __future__ import annotations

from backend.issues.capture import IssueCaptureEngine
from backend.issues.engine import aggregate, issue_to_list_item
from backend.issues.media import attach_snippets, visual_kind_for
from backend.issues.models import UnifiedIssue
from backend.store.issue_screenshots import IssueScreenshotStore


def test_visual_kind_classifies_screenshot_and_snippet():
    assert visual_kind_for("A11Y-CONTRAST-001") == "screenshot"
    assert visual_kind_for("MOBILE-CTA-002") == "screenshot"
    assert visual_kind_for("SEO-H1-002") == "screenshot"
    assert visual_kind_for("SEO-META-001") == "snippet"
    assert visual_kind_for("SEO-ROBOTS-001") == "snippet"
    assert visual_kind_for("SCHEMA-PRESENCE-001") == "snippet"
    assert visual_kind_for("PERF-JS-002") == "none"


def test_snippets_use_stored_head_and_skip_missing_files():
    payload = aggregate(
        "scan_snip",
        {
            "website": {"url": "https://example.com/", "final_url": "https://example.com/"},
            "html": {"title": "Home", "meta_description": None, "canonical": None},
            "robots_txt": {"exists": False, "status_code": 404},
            "sitemap": {"exists": False, "status_code": 404},
            "seo": {
                "checks": [
                    {
                        "check_id": "SEO-META-001",
                        "name": "Meta description exists",
                        "status": "fail",
                        "severity": "high",
                        "message": "No meta description element was found.",
                        "recommendation": "Add a concise unique description.",
                        "why": "Search listings use this summary.",
                        "page_url": "https://example.com/",
                    },
                    {
                        "check_id": "SEO-ROBOTS-001",
                        "name": "robots.txt exists",
                        "status": "warning",
                        "severity": "medium",
                        "message": "robots.txt was not found.",
                        "page_url": "https://example.com/",
                    },
                ]
            },
        },
    )
    by_id = {item.check_id: item for item in payload.issues}
    meta = by_id["SEO-META-001"]
    assert meta.snippet
    assert "meta name=\"description\"" in meta.snippet or "missing" in meta.snippet.lower()
    assert meta.screenshot_url is None
    listed = issue_to_list_item(meta)
    assert listed["snippet"]
    assert listed["whats_wrong"] == meta.description
    assert listed["why_it_matters"] == "Search listings use this summary."
    robots = by_id["SEO-ROBOTS-001"]
    assert robots.snippet
    assert "GET /robots.txt" in robots.snippet
    assert "User-agent" not in robots.snippet
    assert payload.screenshot_capture.visual == 0


def test_list_item_includes_media_fields_without_inventing_screenshots():
    issue = UnifiedIssue.model_validate(
        {
            "issue_id": "issue_1",
            "issue_key": "accessibility.contrast",
            "source": "accessibility",
            "analyzer": "Accessibility Analyzer",
            "category": "Accessibility",
            "check_id": "A11Y-CONTRAST-001",
            "title": "Text has sufficient color contrast",
            "description": "Contrast is 2.8:1 versus 4.5:1 needed.",
            "status": "open",
            "check_status": "fail",
            "severity": "high",
            "priority": "high",
            "priority_score": 80,
            "page_url": "https://example.com/",
            "selector": "p.muted",
            "affected_page_count": 1,
            "pages": ["https://example.com/"],
        }
    )
    listed = issue_to_list_item(issue)
    assert listed["screenshot_url"] is None
    assert listed["snippet"] is None
    assert "screenshot_caption" in listed
    assert listed["viewport_type"] is None


def test_capture_failure_does_not_break_or_fake_screenshots(monkeypatch, tmp_path):
    monkeypatch.setenv("SITEBENCH_ISSUE_SCREENSHOTS", "1")
    payload = aggregate(
        "scan_cap",
        {
            "website": {"url": "https://example.com/", "final_url": "https://example.com/"},
            "accessibility": {
                "checks": [
                    {
                        "check_id": "A11Y-CONTRAST-001",
                        "name": "Text has sufficient color contrast",
                        "status": "fail",
                        "severity": "high",
                        "message": "Contrast is 2.8:1.",
                        "page_url": "https://example.com/",
                        "selector": "p.muted",
                    }
                ]
            },
        },
    )
    engine = IssueCaptureEngine(IssueScreenshotStore(root=tmp_path))

    def boom(*_args, **_kwargs):
        raise RuntimeError("browser exploded")

    monkeypatch.setattr(engine, "_capture_page", boom)
    persisted: list[str] = []
    engine.attach("scan_cap", payload, persist=lambda current: persisted.append(current.screenshot_capture.status))
    assert payload.issues
    assert payload.issues[0].description == "Contrast is 2.8:1."
    assert payload.issues[0].screenshot_url is None
    assert payload.screenshot_capture.status == "completed"
    assert payload.screenshot_capture.note == "Screenshots captured for 0 of 1 visual issues."
    assert "running" in persisted
    assert persisted[-1] == "completed"


def test_screenshot_store_roundtrip_and_delete(tmp_path):
    store = IssueScreenshotStore(root=tmp_path)
    blob = b"RIFF" + b"\x00" * 32
    url = store.put("scan_a", "issue_1", blob, "image/webp")
    assert url == "/api/scans/scan_a/issues/issue_1/screenshot"
    loaded = store.get("scan_a", "issue_1")
    assert loaded is not None
    assert loaded[0] == blob
    store.delete_scan("scan_a")
    assert store.get("scan_a", "issue_1") is None


def test_attach_snippets_skips_when_there_is_nothing_useful():
    issues = [
        UnifiedIssue.model_validate(
            {
                "issue_id": "issue_js",
                "issue_key": "performance.javascript.large_payload",
                "source": "performance",
                "analyzer": "Performance Analyzer",
                "category": "Performance",
                "check_id": "PERF-JS-002",
                "title": "Large JavaScript payload",
                "description": "JavaScript transfer is large.",
                "status": "open",
                "check_status": "warning",
                "severity": "medium",
                "priority": "medium",
                "page_url": "https://example.com/",
            }
        )
    ]
    attach_snippets(issues, {"html": {"title": "Home"}})
    assert issues[0].snippet is None
    assert issues[0].details.get("visual_kind") == "none"
