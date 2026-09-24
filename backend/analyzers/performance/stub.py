"""Deterministic performance results for API tests that must not launch Chromium."""

from __future__ import annotations

from backend.analyzers.performance.analyzer import ProgressFn, analyze_snapshot
from backend.analyzers.performance.models import PerfResult, PerformanceSnapshot


def fast_snapshot(url: str = "https://example.com/") -> PerformanceSnapshot:
    return PerformanceSnapshot.model_validate(
        {
            "page": {"url": url, "final_url": url},
            "environment": {
                "browser": "chromium",
                "browser_version": "stub",
                "viewport": {"width": 1440, "height": 900},
                "viewport_name": "desktop",
                "network_profile": "default",
                "cpu_throttling": False,
                "cache_enabled": False,
                "cache_mode": "cold",
            },
            "timing": {
                "ttfb_ms": 120,
                "dom_content_loaded_ms": 280,
                "load_event_ms": 360,
                "redirect_count": 0,
                "redirect_ms": 0,
                "dns_ms": 10,
                "connection_ms": 20,
            },
            "vitals": {"lcp": {"value": 420, "url": url}, "cls": 0.01, "inp": None, "inp_reason": "No representative interaction was available during the automated run."},
            "resources": [
                {
                    "url": url,
                    "domain": "example.com",
                    "type": "document",
                    "transfer_bytes": 1200,
                    "encoded_bytes": 1200,
                    "decoded_bytes": 2400,
                    "duration_ms": 80,
                    "status": 200,
                    "content_type": "text/html",
                    "first_party": True,
                    "cache_control": "no-store",
                    "content_encoding": "gzip",
                    "etag": False,
                    "last_modified": False,
                }
            ],
            "totals": {
                "total_requests": 1,
                "transfer_bytes": 1200,
                "resource_bytes": 2400,
                "html_bytes": 1200,
                "css_bytes": 0,
                "js_bytes": 0,
                "image_bytes": 0,
                "font_bytes": 0,
                "media_bytes": 0,
                "other_bytes": 0,
                "third_party_bytes": 0,
                "third_party_requests": 0,
                "percentages": {"html": 100, "css": 0, "javascript": 0, "images": 0, "fonts": 0, "third_party": 0},
            },
            "document": {"node_count": 12, "depth": 4, "title": "Example"},
            "scripts": [],
            "stylesheets": [],
            "images": [],
            "hints": [],
            "long_tasks": [],
            "redirects": {"count": 0, "duration_ms": 0},
            "third_party_domains": [],
        }
    )


class StubPerfAnalyzer:
    async def analyze(self, *, url: str, scan_id: str | None = None, on_progress: ProgressFn | None = None) -> PerfResult:
        if on_progress:
            maybe = on_progress(96, "Performance analysis")
            if maybe is not None:
                await maybe
        return analyze_snapshot(fast_snapshot(url))
