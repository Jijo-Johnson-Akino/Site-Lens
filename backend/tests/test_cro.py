from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.analyzers.accessibility.stub import StubA11yAnalyzer
from backend.analyzers.cro import analyze_cro
from backend.analyzers.cro.config import FORM_FIELD_HIGH_THRESHOLD, FORM_FIELD_WARNING_THRESHOLD
from backend.analyzers.cro.extraction import (
    classify_destination,
    extract_signals,
)
from backend.analyzers.cro.scoring import overall_score
from backend.analyzers.mobile.stub import StubMobileAnalyzer
from backend.analyzers.performance.stub import StubPerfAnalyzer
from backend.analyzers.uiux.stub import StubUiuxAnalyzer
from backend.api import scans as scans_api
from backend.errors import ScanError
from backend.issues.engine import aggregate
from backend.issues.keys import issue_key_for
from backend.main import app
from backend.pages.ids import make_link_id, make_page_id
from backend.pages.models import InternalLink, PageRecord, PagesPayload
from backend.recommendations.engine import generate
from backend.recommendations.registry import mapped_issue_keys
from backend.services.scan_service import ScanService
from backend.services.url_identity import normalize_page_url
from backend.services.url_validator import UrlValidator
from backend.services.website_fetcher import WebsiteFetcher
from backend.store.scans import InMemoryScanStore
from backend.store.screenshots import InMemoryScreenshotStore

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "cro"


def load(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def _page(scan_id: str, url: str, html: str, *, page_type: str, is_seed: bool = False) -> PageRecord:
    normalized = normalize_page_url(url)
    signals = extract_signals(html, url)
    return PageRecord(
        id=make_page_id(scan_id, normalized),
        scan_id=scan_id,
        url=url,
        normalized_url=normalized,
        final_url=url,
        crawl_status="crawled",
        page_type=page_type,
        title=signals.get("h1"),
        h1=signals.get("h1"),
        cro_signals=signals,
        is_seed=is_seed,
        http_status=200,
        discovery_method="seed" if is_seed else "internal_link",
    )


def _link(scan_id: str, source: PageRecord, dest: PageRecord, anchor: str = "") -> InternalLink:
    return InternalLink(
        id=make_link_id(scan_id, source.id, dest.id, anchor),
        scan_id=scan_id,
        source_page_id=source.id,
        destination_page_id=dest.id,
        source_url=source.normalized_url,
        destination_url=dest.normalized_url,
        anchor_text=anchor,
    )


def desktop_viewport(
    *,
    text: str = "Start Free Trial",
    href: str = "/signup",
    in_viewport: bool = True,
    clipped: bool = False,
    visible: bool = True,
    overlays: list | None = None,
    nav_links: int = 4,
    buttons: list | None = None,
    forms: list | None = None,
) -> dict:
    button_list = buttons if buttons is not None else [
        {
            "text": text,
            "kind": "button",
            "in_viewport": in_viewport,
            "visible": visible,
            "clipped": clipped,
            "width": 180,
            "height": 48,
            "href": href,
            "selector": "a.cta",
            "disabled": False,
        }
    ]
    return {
        "cta": {
            "exists": True,
            "text": text,
            "in_viewport": in_viewport,
            "visible": visible,
            "clipped": clipped,
            "selector": "a.cta",
        },
        "buttons": button_list,
        "links": [],
        "forms": forms or [],
        "overlays": overlays or [],
        "navigation": {"exists": True, "visible": True, "links": nav_links},
        "headings": [{"text": "AI Payroll Software for Growing Businesses", "visible": True, "in_viewport": True}],
        "content": {"h1": 1, "h1_visible": True, "paragraphs": 1},
    }


def site_pages(scan_id: str = "scan_cro") -> PagesPayload:
    home = _page(scan_id, "https://example.com/", load("home.html"), page_type="homepage", is_seed=True)
    contact = _page(scan_id, "https://example.com/contact", load("contact.html"), page_type="contact")
    pricing = _page(scan_id, "https://example.com/pricing", load("pricing.html"), page_type="pricing")
    blog = _page(scan_id, "https://example.com/blog", load("blog.html"), page_type="article")
    items = [home, contact, pricing, blog]
    links = [
        _link(scan_id, home, contact, "Contact"),
        _link(scan_id, home, pricing, "Pricing"),
        _link(scan_id, home, blog, "Blog"),
        _link(scan_id, pricing, home, "Home"),
    ]
    return PagesPayload(items=items, internal_links=links, internal_links_recorded=True)


def analyze(pages: PagesPayload, *, desktop: dict | None = None, mobile: dict | None = None, a11y: dict | None = None) -> object:
    seed = next(page for page in pages.items if page.is_seed)
    payload: dict = {
        "website": {"url": seed.url, "final_url": seed.url},
        "html": {"h1": seed.h1},
    }
    if desktop is not None:
        payload["uiux"] = {
            "viewports": {"desktop": desktop},
            "screenshots": [{"viewport": "desktop", "width": 1440, "height": 900, "url": "/shot"}],
        }
    if mobile is not None:
        payload["mobile"] = mobile
    if a11y is not None:
        payload["accessibility"] = a11y
    return analyze_cro(payload, pages=pages)


def by_id(result, check_id: str, page_url: str | None = None):
    matches = [item for item in result.checks if item.check_id == check_id]
    if page_url:
        matches = [item for item in matches if item.page_url.rstrip("/") == page_url.rstrip("/")]
    assert matches, f"expected {check_id} on {page_url or 'any page'}"
    return matches[0]


def test_cta_detection_and_destination():
    signals = extract_signals(load("home.html"), "https://example.com/")
    texts = {item["text"] for item in signals["ctas"]}
    assert "Start Free Trial" in texts
    assert "Book Demo" in texts
    trial = next(item for item in signals["ctas"] if item["text"] == "Start Free Trial")
    assert trial["destination"] == "signup"
    assert trial["primary_candidate"] is True
    assert classify_destination("/contact", "https://example.com/") == "contact"
    assert classify_destination("/pricing", "https://example.com/") == "pricing"
    assert classify_destination("https://other.example/x", "https://example.com/") == "external"
    assert classify_destination("#", "https://example.com/") == "unknown"


def test_cta_visibility_clarity_competing_and_consistency():
    pages = site_pages()
    visible = analyze(
        pages,
        desktop=desktop_viewport(in_viewport=True),
        mobile={"cta": {"exists": True, "text": "Start Free Trial", "in_viewport": True, "clipped": False}, "forms": {"overflowing_forms": 0}},
    )
    home = "https://example.com/"
    assert by_id(visible, "cro.cta.primary.missing", home).status == "pass"
    assert by_id(visible, "cro.cta.primary.not_visible", home).status == "pass"
    assert "not visible within the initial viewport" not in by_id(visible, "cro.cta.primary.not_visible", home).message.lower() or by_id(visible, "cro.cta.primary.not_visible", home).status == "pass"
    hidden = analyze(pages, desktop=desktop_viewport(in_viewport=False, clipped=True))
    assert by_id(hidden, "cro.cta.primary.not_visible", home).status == "fail"
    assert "not visible within the initial viewport" in by_id(hidden, "cro.cta.primary.not_visible", home).message.lower()

    vague_page = _page("scan_vague", "https://example.com/", load("vague_cta.html"), page_type="homepage", is_seed=True)
    vague = analyze(PagesPayload(items=[vague_page]))
    assert by_id(vague, "cro.cta.text.vague").status == "warning"

    competing_page = _page("scan_comp", "https://example.com/", load("competing.html"), page_type="homepage", is_seed=True)
    competing = analyze(PagesPayload(items=[competing_page]))
    assert by_id(competing, "cro.cta.multiple_competing").status == "warning"
    assert "Multiple prominent actions" in by_id(competing, "cro.cta.multiple_competing").message
    assert by_id(visible, "cro.cta.inconsistent_label", home).status == "warning"


def test_broken_cta_destination():
    page = _page("scan_broken", "https://example.com/", load("broken_cta.html"), page_type="homepage", is_seed=True)
    result = analyze(PagesPayload(items=[page]))
    check = by_id(result, "cro.cta.destination.unresolved")
    assert check.status == "warning"
    assert "could not be resolved" in check.message.lower() or "disabled" in check.message.lower()


def test_form_detection_length_purpose_and_friction():
    contact = _page("scan_form", "https://example.com/contact", load("contact.html"), page_type="contact", is_seed=True)
    result = analyze(PagesPayload(items=[contact]))
    assert by_id(result, "cro.form.missing").status == "pass"
    length = by_id(result, "cro.form.large")
    assert length.status == "warning"
    assert "5" in length.message
    assert FORM_FIELD_WARNING_THRESHOLD == 5
    assert by_id(result, "cro.form.unclear_purpose").status == "pass"
    assert result.forms[0].purpose == "Contact"
    assert result.forms[0].fields == 5
    assert result.forms[0].submit_text == "Send Message"

    large = _page("scan_large", "https://example.com/contact", load("large_form.html"), page_type="contact", is_seed=True)
    large_result = analyze(PagesPayload(items=[large]))
    large_check = by_id(large_result, "cro.form.large")
    assert large_check.status == "warning"
    assert str(FORM_FIELD_HIGH_THRESHOLD) in large_check.message or "9" in large_check.message
    assert "higher interaction effort" in large_check.message


def test_value_proposition_and_page_types():
    pages = site_pages()
    result = analyze(pages, desktop=desktop_viewport())
    home = "https://example.com/"
    assert by_id(result, "cro.value_proposition.h1_missing", home).status == "pass"
    assert by_id(result, "cro.value_proposition.supporting_text_missing", home).status == "pass"
    assert by_id(result, "cro.value_proposition.cta_missing", home).status == "pass"
    blog = "https://example.com/blog"
    assert by_id(result, "cro.cta.primary.missing", blog).status == "not_applicable"
    assert by_id(result, "cro.value_proposition.h1_missing", blog).status == "not_applicable"

    missing = _page("scan_vp", "https://example.com/", load("missing_value.html"), page_type="homepage", is_seed=True)
    weak = analyze(PagesPayload(items=[missing]))
    assert by_id(weak, "cro.value_proposition.h1_missing").status in {"fail", "warning"}
    assert by_id(weak, "cro.value_proposition.supporting_text_missing").status == "warning"


def test_contact_pricing_and_quote_without_public_price():
    pages = site_pages()
    result = analyze(pages, desktop=desktop_viewport())
    assert by_id(result, "cro.contact.method.missing", "https://example.com/").status == "pass"
    assert by_id(result, "cro.pricing.offer.not_detected", "https://example.com/pricing").status == "pass"
    quote = _page("scan_quote", "https://example.com/", load("quote.html"), page_type="service", is_seed=True)
    quoted = analyze(PagesPayload(items=[quote]))
    assert by_id(quoted, "cro.pricing.offer.not_detected").status == "pass"
    missing_contact = _page("scan_nc", "https://example.com/", load("missing_cta.html"), page_type="homepage", is_seed=True)
    isolated = analyze(PagesPayload(items=[missing_contact]))
    assert by_id(isolated, "cro.contact.method.missing").status == "warning"


def test_conversion_path_from_crawled_links():
    pages = site_pages()
    result = analyze(pages, desktop=desktop_viewport())
    home_path = by_id(result, "cro.conversion_path.unresolved", "https://example.com/")
    assert home_path.status == "pass"
    assert result.conversion_paths
    nodes = result.conversion_paths[0].nodes
    assert nodes
    assert nodes[0].page_type == "homepage"
    assert any(node.page_type in {"contact", "pricing"} for node in nodes)
    empty = _page("scan_nopath", "https://example.com/", load("missing_cta.html"), page_type="homepage", is_seed=True)
    unresolved = analyze(PagesPayload(items=[empty], internal_links_recorded=True))
    assert by_id(unresolved, "cro.conversion_path.unresolved").status == "warning"
    assert unresolved.conversion_paths[0].message or unresolved.conversion_paths[0].nodes == []


def test_mobile_cta_and_overlay_coverage():
    pages = site_pages()
    hidden_mobile = analyze(
        pages,
        desktop=desktop_viewport(),
        mobile={"cta": {"exists": True, "text": "Start Free Trial", "in_viewport": False, "clipped": True}, "forms": {"overflowing_forms": 1}},
    )
    assert by_id(hidden_mobile, "cro.mobile.cta.not_visible", "https://example.com/").status == "warning"
    covered = analyze(
        pages,
        desktop=desktop_viewport(overlays=[{"coverage": 0.8, "selector": ".modal"}]),
    )
    overlay = by_id(covered, "cro.overlay.cta.covered", "https://example.com/")
    assert overlay.status == "warning"
    assert "covering the primary CTA" in overlay.message
    blog_only = PagesPayload(
        items=[_page("scan_blog", "https://example.com/blog", load("blog.html"), page_type="article", is_seed=True)]
    )
    unrendered = analyze(blog_only)
    assert by_id(unrendered, "cro.mobile.cta.not_visible").status == "not_applicable"
    assert by_id(unrendered, "cro.overlay.cta.covered").status == "not_applicable"


def test_scoring_is_deterministic_and_na_is_excluded():
    pages = site_pages()
    first = analyze(pages, desktop=desktop_viewport(), mobile={"cta": {"exists": True, "in_viewport": True}, "forms": {}})
    second = analyze(pages, desktop=desktop_viewport(), mobile={"cta": {"exists": True, "in_viewport": True}, "forms": {}})
    assert first.score == second.score
    assert first.score is not None
    assert 0 <= first.score <= 100
    blob = " ".join([first.narrative, first.score_note] + [item.message for item in first.checks]).lower()
    assert "conversion probability" not in blob
    assert "guaranteed conversion" not in blob
    assert "will increase revenue" not in blob
    assert "does not measure actual conversion rates" in first.methodology.lower()
    article = PagesPayload(items=[_page("scan_na", "https://example.com/blog", load("blog.html"), page_type="article", is_seed=True)])
    article_result = analyze(article)
    na_checks = [item for item in article_result.checks if item.status == "not_applicable"]
    assert na_checks
    applicable = [item for item in article_result.checks if item.status != "not_applicable"]
    if not applicable:
        assert article_result.score is None
    else:
        assert overall_score(article_result.checks) == article_result.score


def test_missing_cta_homepage_fails_primary():
    page = _page("scan_miss", "https://example.com/", load("missing_cta.html"), page_type="homepage", is_seed=True)
    result = analyze(PagesPayload(items=[page]))
    assert by_id(result, "cro.cta.primary.missing").status == "fail"
    assert result.score is not None


def test_issues_and_recommendations_from_cro_findings():
    page = _page("scan_issues", "https://example.com/", load("missing_cta.html"), page_type="homepage", is_seed=True)
    cro = analyze(PagesPayload(items=[page]))
    result = {
        "website": {"url": "https://example.com/", "final_url": "https://example.com/"},
        "cro": cro.model_dump(mode="json"),
    }
    issues = aggregate("scan_issues", result, "2026-01-01T00:00:00+00:00")
    keys = {item.issue_key for item in issues.issues}
    assert "cro.cta.primary.missing" in keys
    assert issue_key_for("cro", "cro.cta.primary.not_visible") == "cro.cta.primary.not_visible"
    assert "cro.cta.primary.not_visible" in mapped_issue_keys()
    result["issues"] = issues.model_dump(mode="json")
    recs = generate("scan_issues", result, "2026-01-01T00:00:00+00:00")
    rec_keys = {item.recommendation_key for item in recs.recommendations}
    assert "cro.add_primary_cta" in rec_keys
    assert all(item.category == "CRO" for item in recs.recommendations if item.recommendation_key.startswith("cro."))


def test_scan_isolation_and_partial_analysis():
    a = site_pages("scan_a")
    b = PagesPayload(items=[_page("scan_b", "https://other.example/", load("missing_cta.html"), page_type="homepage", is_seed=True)])
    left = analyze(a, desktop=desktop_viewport())
    right = analyze(b)
    assert all("other.example" not in item.page_url for item in left.checks)
    assert all(item.page_url.startswith("https://other.example") for item in right.checks)
    with pytest.raises(ScanError) as exc:
        analyze_cro({}, pages=PagesPayload())
    assert exc.value.code == "CRO_FAILED"


def public_dns(_host: str, _port: int) -> list[str]:
    return ["93.184.216.34"]


PAGES = {
    "/": load("home.html"),
    "/contact": load("contact.html"),
    "/pricing": load("pricing.html"),
    "/blog": load("blog.html"),
    "/signup": "<!doctype html><html><head><title>Sign up</title></head><body><h1>Create account</h1><form><label for='e'>Email</label><input id='e' type='email'><button>Create Account</button></form></body></html>",
    "/demo": "<!doctype html><html><head><title>Demo</title></head><body><h1>Book a demo</h1></body></html>",
}


def cro_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path in {"/robots.txt", "/sitemap.xml", "/llms.txt"}:
        return httpx.Response(404, text="missing")
    html = PAGES.get(path)
    if html is None:
        return httpx.Response(404, text="missing")
    return httpx.Response(200, text=html, headers={"content-type": "text/html"})


@pytest.fixture
def cro_client() -> TestClient:
    store = InMemoryScanStore()
    shots = InMemoryScreenshotStore()
    validator = UrlValidator(resolver=public_dns)
    fetcher = WebsiteFetcher(
        validator=validator,
        client=httpx.AsyncClient(transport=httpx.MockTransport(cro_handler), follow_redirects=False),
    )
    scans_api.service = ScanService(
        store=store,
        validator=validator,
        fetcher=fetcher,
        uiux_analyzer=StubUiuxAnalyzer(shots),
        a11y_analyzer=StubA11yAnalyzer(),
        perf_analyzer=StubPerfAnalyzer(),
        mobile_analyzer=StubMobileAnalyzer(shots),
        screenshot_store=shots,
    )
    return TestClient(app)


def test_cro_api_fixture_scan(cro_client: TestClient) -> None:
    created = cro_client.post("/api/scans", json={"url": "https://example.com"})
    assert created.status_code == 202
    scan_id = created.json()["scan_id"]
    payload = cro_client.get(f"/api/scans/{scan_id}").json()
    assert payload["status"] == "completed"
    cro_payload = payload["result"]["cro"]
    assert cro_payload is not None
    assert isinstance(cro_payload["score"], int)
    assert 0 <= cro_payload["score"] <= 100
    joined = str(cro_payload).lower()
    assert "conversion probability" not in joined
    assert "revenue increase" not in joined
    assert "guaranteed conversion" not in joined
    api = cro_client.get(f"/api/scans/{scan_id}/cro")
    assert api.status_code == 200
    body = api.json()
    assert body["scan_id"] == scan_id
    assert body["score"] == cro_payload["score"]
    assert body["summary"]["pages_analyzed"] >= 1
    assert body["pages"]
    assert body["methodology"]
    assert "does not measure actual conversion rates" in body["methodology"]
    ids = {item["check_id"] for item in body["checks"]}
    assert "cro.cta.primary.missing" in ids
    page_id = body["pages"][0]["page_id"]
    detail = cro_client.get(f"/api/scans/{scan_id}/cro/pages/{page_id}")
    assert detail.status_code == 200
    assert detail.json()["page"]["page_id"] == page_id
    missing = cro_client.get(f"/api/scans/{scan_id}/cro/pages/page_does_not_exist")
    assert missing.status_code == 404
    issues = cro_client.get(f"/api/scans/{scan_id}/issues", params={"category": "CRO"})
    assert issues.status_code == 200
    assert all(item["category"] == "CRO" for item in issues.json()["items"])
    recs = cro_client.get(f"/api/scans/{scan_id}/recommendations", params={"category": "CRO"})
    assert recs.status_code == 200
    pages = cro_client.get(f"/api/scans/{scan_id}/pages")
    assert pages.status_code == 200
    architecture = cro_client.get(f"/api/scans/{scan_id}/architecture")
    assert architecture.status_code == 200
    other = cro_client.post("/api/scans", json={"url": "https://example.com"})
    other_id = other.json()["scan_id"]
    isolated = cro_client.get(f"/api/scans/{other_id}/cro")
    assert isolated.status_code == 200
    leak = cro_client.get(f"/api/scans/{other_id}/cro/pages/{page_id}")
    assert leak.status_code == 404


def test_cro_failure_preserves_other_results(cro_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail(*_args, **_kwargs):
        raise ScanError("CRO_FAILED", "CRO analysis could not be completed.")

    monkeypatch.setattr("backend.services.scan_service.analyze_cro", _fail)
    created = cro_client.post("/api/scans", json={"url": "https://example.com"})
    scan_id = created.json()["scan_id"]
    payload = cro_client.get(f"/api/scans/{scan_id}").json()
    assert payload["status"] == "completed"
    assert payload["result"]["seo"]["score"] is not None
    assert payload["result"]["mobile"]["score"] is not None
    assert payload["result"]["cro"] is None
    assert payload["result"]["cro_error"]["code"] == "CRO_FAILED"
    cro = cro_client.get(f"/api/scans/{scan_id}/cro")
    assert cro.status_code == 404
    assert cro.json()["error"]["code"] == "CRO_FAILED"
    issues = cro_client.get(f"/api/scans/{scan_id}/issues")
    assert issues.status_code == 200
    recs = cro_client.get(f"/api/scans/{scan_id}/recommendations")
    assert recs.status_code == 200
    pages = cro_client.get(f"/api/scans/{scan_id}/pages")
    assert pages.status_code == 200
    architecture = cro_client.get(f"/api/scans/{scan_id}/architecture")
    assert architecture.status_code == 200
