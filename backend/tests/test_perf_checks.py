from __future__ import annotations

from backend.tests.perf_helpers import analyze_dom, by_id, snapshot_with


def test_fast_snapshot_scores_well() -> None:
    result = analyze_dom()
    assert result.summary.failed == 0
    assert result.score >= 90
    assert by_id(result, "PERF-TTFB-001").status == "pass"
    assert by_id(result, "PERF-VITAL-003").status == "not_applicable"
    assert result.vitals.inp.status == "unavailable"
    assert result.vitals.inp.value is None
    assert "automated" in " ".join(result.limitations).lower()


def test_slow_ttfb() -> None:
    result = analyze_dom(snapshot_with(timing={"ttfb_ms": 2100, "dom_content_loaded_ms": 280, "load_event_ms": 360}))
    check = by_id(result, "PERF-TTFB-001")
    assert check.status == "fail"
    assert "2100" in (check.detected or check.message) or "2.10s" in (check.detected or check.message)


def test_large_javascript() -> None:
    result = analyze_dom(snapshot_with(totals={"js_bytes": 1_200_000, "transfer_bytes": 1_200_000, "total_requests": 2, "html_bytes": 1200, "css_bytes": 0, "image_bytes": 0, "font_bytes": 0, "resource_bytes": 1_200_000, "third_party_bytes": 0, "third_party_requests": 0, "percentages": {}}))
    assert by_id(result, "PERF-JS-002").status == "warning"


def test_parser_blocking_js() -> None:
    result = analyze_dom(snapshot_with(scripts=[{"src": "https://example.com/app.js", "async": False, "defer": False, "inline_bytes": 0, "in_head": True}]))
    assert by_id(result, "PERF-JS-001").status in {"warning", "fail"}
    assert by_id(result, "PERF-BLOCK-001").status in {"warning", "fail"}


def test_large_image() -> None:
    result = analyze_dom(
        snapshot_with(
            resources=[
                {
                    "url": "https://example.com/hero.jpg",
                    "domain": "example.com",
                    "type": "image",
                    "transfer_bytes": 1_200_000,
                    "encoded_bytes": 1_200_000,
                    "decoded_bytes": 1_200_000,
                    "first_party": True,
                    "status": 200,
                }
            ]
        )
    )
    assert by_id(result, "PERF-IMG-001").status == "warning"


def test_oversized_and_lazy_images() -> None:
    result = analyze_dom(
        snapshot_with(
            images=[
                {
                    "src": "https://example.com/below.png",
                    "natural_width": 2400,
                    "natural_height": 1600,
                    "rendered_width": 400,
                    "rendered_height": 267,
                    "loading": "",
                    "srcset": False,
                    "below_fold": True,
                }
            ]
        )
    )
    assert by_id(result, "PERF-IMG-002").status == "warning"
    assert by_id(result, "PERF-IMG-003").status == "warning"


def test_srcset_not_flagged_as_oversized() -> None:
    result = analyze_dom(
        snapshot_with(
            images=[
                {
                    "src": "https://example.com/r.png",
                    "natural_width": 2400,
                    "rendered_width": 400,
                    "srcset": True,
                    "below_fold": False,
                    "loading": "lazy",
                }
            ]
        )
    )
    assert by_id(result, "PERF-IMG-002").status == "pass"


def test_compression_missing_on_text() -> None:
    result = analyze_dom(
        snapshot_with(
            resources=[
                {
                    "url": "https://example.com/app.js",
                    "type": "script",
                    "transfer_bytes": 80_000,
                    "encoded_bytes": 80_000,
                    "content_encoding": None,
                    "content_type": "application/javascript",
                    "first_party": True,
                }
            ]
        )
    )
    assert by_id(result, "PERF-COMP-001").status == "warning"


def test_compression_present() -> None:
    result = analyze_dom(
        snapshot_with(
            resources=[
                {
                    "url": "https://example.com/app.js",
                    "type": "script",
                    "transfer_bytes": 80_000,
                    "encoded_bytes": 80_000,
                    "content_encoding": "br",
                    "content_type": "application/javascript",
                    "first_party": True,
                }
            ]
        )
    )
    assert by_id(result, "PERF-COMP-001").status == "pass"


def test_cache_headers_missing_on_static() -> None:
    result = analyze_dom(
        snapshot_with(
            resources=[
                {
                    "url": "https://example.com/app.js",
                    "type": "script",
                    "transfer_bytes": 4000,
                    "cache_control": None,
                    "etag": False,
                    "last_modified": False,
                    "expires": None,
                    "first_party": True,
                }
            ]
        )
    )
    assert by_id(result, "PERF-CACHE-001").status == "warning"


def test_html_not_required_to_be_cached() -> None:
    result = analyze_dom()
    assert by_id(result, "PERF-CACHE-001").status == "not_applicable"


def test_multiple_redirects() -> None:
    result = analyze_dom(snapshot_with(redirects={"count": 3, "duration_ms": 400}, timing={"redirect_count": 3, "redirect_ms": 400}))
    assert by_id(result, "PERF-REDIR-001").status == "fail"


def test_single_https_redirect_is_not_a_failure() -> None:
    result = analyze_dom(snapshot_with(redirects={"count": 1, "duration_ms": 40}, timing={"redirect_count": 1}))
    assert by_id(result, "PERF-REDIR-001").status == "pass"


def test_third_party_weight() -> None:
    result = analyze_dom(
        snapshot_with(
            totals={
                "total_requests": 10,
                "transfer_bytes": 100_000,
                "third_party_bytes": 50_000,
                "third_party_requests": 20,
                "html_bytes": 1200,
                "js_bytes": 0,
                "css_bytes": 0,
                "image_bytes": 0,
                "font_bytes": 0,
                "resource_bytes": 100_000,
                "percentages": {},
            },
            third_party_domains=[{"domain": "cdn.example.net", "requests": 20, "bytes": 50_000}],
        )
    )
    assert by_id(result, "PERF-TP-001").status == "warning"


def test_large_dom() -> None:
    result = analyze_dom(snapshot_with(document={"node_count": 3200, "depth": 18, "title": "Big"}))
    assert by_id(result, "PERF-DOM-001").status == "warning"


def test_long_tasks() -> None:
    result = analyze_dom(snapshot_with(long_tasks=[{"duration": 80, "start": 10}] * 10))
    assert by_id(result, "PERF-LONG-001").status == "warning"


def test_lcp_and_cls_from_snapshot() -> None:
    good = analyze_dom()
    assert by_id(good, "PERF-VITAL-001").status == "pass"
    assert good.vitals.lcp.value == 420
    poor = analyze_dom(snapshot_with(vitals={"lcp": {"value": 5000, "url": "/"}, "cls": 0.4}))
    assert by_id(poor, "PERF-VITAL-001").status == "fail"
    assert by_id(poor, "PERF-VITAL-002").status == "fail"


def test_unavailable_lcp_is_not_zero() -> None:
    result = analyze_dom(snapshot_with(vitals={"lcp": None, "cls": 0.01}))
    assert by_id(result, "PERF-VITAL-001").status == "not_applicable"
    assert result.vitals.lcp.value is None
    assert result.vitals.lcp.status == "unavailable"


def test_inp_is_unavailable_without_interaction() -> None:
    result = analyze_dom()
    assert result.vitals.inp.value is None
    assert result.vitals.inp.status == "unavailable"
    assert "interaction" in (result.vitals.inp.reason or "").lower()
    assert by_id(result, "PERF-VITAL-003").status == "not_applicable"


def test_large_css_payload() -> None:
    result = analyze_dom(snapshot_with(totals={"css_bytes": 400_000, "transfer_bytes": 400_000}))
    assert by_id(result, "PERF-CSS-001").status == "warning"


def test_lcp_image_is_not_flagged_for_lazy_loading() -> None:
    result = analyze_dom(
        snapshot_with(
            vitals={"lcp": {"value": 900, "url": "https://example.com/hero.png"}, "cls": 0.01},
            images=[
                {
                    "src": "https://example.com/hero.png",
                    "natural_width": 800,
                    "rendered_width": 800,
                    "loading": "",
                    "srcset": False,
                    "below_fold": True,
                }
            ],
        )
    )
    assert by_id(result, "PERF-IMG-003").status == "pass"


def test_sensitive_query_params_are_stripped() -> None:
    from backend.analyzers.performance.sanitize import sanitize_url

    cleaned = sanitize_url("https://cdn.example.com/app.js?token=secret&v=2")
    assert "secret" not in cleaned
    assert "token=" not in cleaned
    assert "v=2" in cleaned
