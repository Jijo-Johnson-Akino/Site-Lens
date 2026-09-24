from __future__ import annotations

import httpx
import pytest

from backend.pages.crawler import crawl_site
from backend.pages.engine import attach_issues
from backend.pages.query import query_pages
from backend.services.url_identity import normalize_page_url
from backend.services.url_validator import UrlValidator
from backend.services.website_fetcher import WebsiteFetcher

HOME = """<!doctype html><html lang="en"><head>
<title>Fixture Home</title>
<meta name="description" content="Home description">
<link rel="canonical" href="https://example.com/">
</head><body>
<h1>Homepage</h1>
<p>Welcome to the fixture site used for Pages Explorer crawl tests.</p>
<ul><li>One</li><li>Two</li></ul>
<a href="/about">About</a>
<a href="/about/">About slash</a>
<a href="/about#team">About fragment</a>
<a href="/contact">Contact</a>
<a href="/blog">Blog</a>
<a href="/product">Product</a>
<a href="/missing">Broken</a>
<a href="/logo.png">Logo</a>
<a href="https://other.example/offsite">Offsite</a>
</body></html>"""

ABOUT = """<!doctype html><html lang="en"><head><title>About us</title></head>
<body><h1>About</h1><p>This is the about page with enough words to classify conservatively.</p>
<a href="/">Home</a></body></html>"""

CONTACT = """<!doctype html><html lang="en"><head><title>Contact</title></head>
<body><h1>Contact</h1><form><label>Email</label><input type="email"></form>
<p>Reach the team through this contact page.</p></body></html>"""

BLOG = """<!doctype html><html lang="en"><head><title>Blog</title></head>
<body><h1>Blog</h1><p>Listing of articles.</p><a href="/blog/article">Read article</a></body></html>"""

ARTICLE = """<!doctype html><html lang="en"><head><title>A long article</title>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Article","headline":"A long article"}</script>
</head><body><article><h1>A long article</h1><h2>One</h2><p>Word """ + ("content " * 80) + """</p>
<h2>Two</h2><p>More words for the classifier.</p></article></body></html>"""

PRODUCT = """<!doctype html><html lang="en"><head><title>Product</title>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Product","name":"Widget"}</script>
</head><body><h1>Product</h1><p>A product page.</p></body></html>"""

MISSING = """<!doctype html><html><head><title>Not found</title></head><body><h1>404</h1></body></html>"""

SITEMAP = """<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://example.com/contact</loc></url>
<url><loc>https://example.com/product</loc></url>
</urlset>"""

PAGES = {
    "/": HOME,
    "/about": ABOUT,
    "/about/": ABOUT,
    "/contact": CONTACT,
    "/blog": BLOG,
    "/blog/article": ARTICLE,
    "/product": PRODUCT,
    "/missing": MISSING,
}


def public_dns(_host: str, _port: int) -> list[str]:
    return ["93.184.216.34"]


def handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/robots.txt":
        return httpx.Response(404, text="missing")
    if path == "/sitemap.xml":
        return httpx.Response(200, text=SITEMAP, headers={"content-type": "application/xml"})
    if path == "/logo.png":
        return httpx.Response(200, content=b"\x89PNG", headers={"content-type": "image/png"})
    if path == "/pdf":
        return httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"})
    if path == "/slow":
        raise httpx.ReadTimeout("slow")
    if path == "/private-redirect":
        return httpx.Response(302, headers={"location": "http://127.0.0.1/"})
    if path == "/off-host":
        return httpx.Response(302, headers={"location": "https://other.example/"})
    body = PAGES.get(path)
    if body is None:
        return httpx.Response(404, text=MISSING, headers={"content-type": "text/html"})
    status = 404 if path == "/missing" else 200
    return httpx.Response(status, text=body, headers={"content-type": "text/html"})


@pytest.fixture
def fetcher() -> WebsiteFetcher:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)
    return WebsiteFetcher(validator=UrlValidator(resolver=public_dns), client=client)


def _seed_fetch(html: str, path: str = "/") -> dict:
    return {
        "status_code": 200,
        "final_url": f"https://example.com{path}",
        "response_time_ms": 12,
        "content_type": "text/html",
        "html": html,
        "html_size_bytes": len(html.encode("utf-8")),
        "x_robots_tag": None,
    }


@pytest.mark.asyncio
async def test_fixture_site_discovers_internal_pages(fetcher: WebsiteFetcher) -> None:
    from backend.parser.html_parser import parse_html

    html_data = parse_html(HOME)
    payload = await crawl_site(
        scan_id="scan_pages_fixture",
        seed_url="https://example.com/",
        seed_fetch=_seed_fetch(HOME),
        seed_html=HOME,
        seed_html_data=html_data,
        fetcher=fetcher,
        allowed_host="example.com",
        sitemap_body=SITEMAP,
        max_pages=50,
        max_depth=3,
    )
    urls = {item.normalized_url for item in payload.items}
    assert "https://example.com/" in urls
    assert "https://example.com/about" in urls
    assert "https://example.com/contact" in urls
    assert "https://example.com/blog" in urls
    assert "https://example.com/blog/article" in urls
    assert "https://example.com/product" in urls
    assert "https://example.com/missing" in urls
    assert not any(item.normalized_url.endswith(".png") for item in payload.items)
    abouts = [item for item in payload.items if item.normalized_url == "https://example.com/about"]
    assert len(abouts) == 1
    crawled = [item for item in payload.items if item.crawl_status == "crawled"]
    assert len(crawled) >= 6
    types = {item.page_type for item in payload.items if item.crawl_status == "crawled"}
    assert "homepage" in types
    assert payload.summary.external_links_discovered >= 1
    missing = next(item for item in payload.items if item.normalized_url.endswith("/missing"))
    assert missing.http_status == 404
    assert missing.crawl_status == "crawled"
    dests = {link.destination_url for link in payload.internal_links}
    sources = {link.source_url for link in payload.internal_links}
    assert "https://example.com/about" in dests
    assert "https://example.com/" in sources
    assert not any(link.destination_url.endswith(".png") for link in payload.internal_links)
    assert not any("other.example" in link.destination_url for link in payload.internal_links)
    ids = [link.id for link in payload.internal_links]
    assert len(ids) == len(set(ids))


@pytest.mark.asyncio
async def test_max_pages_enforced(fetcher: WebsiteFetcher) -> None:
    from backend.parser.html_parser import parse_html

    payload = await crawl_site(
        scan_id="scan_limit",
        seed_url="https://example.com/",
        seed_fetch=_seed_fetch(HOME),
        seed_html=HOME,
        seed_html_data=parse_html(HOME),
        fetcher=fetcher,
        allowed_host="example.com",
        max_pages=2,
        max_depth=3,
    )
    assert payload.summary.crawled <= 2
    assert payload.summary.page_limit_reached is True
    assert any(item.crawl_status == "skipped" and item.skip_reason for item in payload.items)


@pytest.mark.asyncio
async def test_max_depth_enforced(fetcher: WebsiteFetcher) -> None:
    from backend.parser.html_parser import parse_html

    payload = await crawl_site(
        scan_id="scan_depth",
        seed_url="https://example.com/",
        seed_fetch=_seed_fetch(HOME),
        seed_html=HOME,
        seed_html_data=parse_html(HOME),
        fetcher=fetcher,
        allowed_host="example.com",
        max_pages=50,
        max_depth=1,
    )
    article = next((item for item in payload.items if item.normalized_url.endswith("/blog/article")), None)
    if article:
        assert article.crawl_status == "skipped"
        assert article.skip_reason
        assert article.depth > 1
    assert payload.summary.max_depth_reached >= 1


@pytest.mark.asyncio
async def test_failed_and_skipped_persistence(fetcher: WebsiteFetcher) -> None:
    from backend.parser.html_parser import parse_html

    html = HOME.replace('href="/missing"', 'href="/slow"').replace('href="/logo.png"', 'href="/pdf"')
    payload = await crawl_site(
        scan_id="scan_fail",
        seed_url="https://example.com/",
        seed_fetch=_seed_fetch(html),
        seed_html=html,
        seed_html_data=parse_html(html),
        fetcher=fetcher,
        allowed_host="example.com",
        max_pages=50,
        max_depth=2,
    )
    failed = [item for item in payload.items if item.normalized_url.endswith("/slow")]
    skipped_pdf = [item for item in payload.items if item.normalized_url.endswith("/pdf")]
    assert failed and failed[0].crawl_status == "failed"
    assert failed[0].failure_reason
    assert "traceback" not in (failed[0].failure_reason or "").lower()
    assert skipped_pdf and skipped_pdf[0].crawl_status == "skipped"
    assert skipped_pdf[0].skip_reason


@pytest.mark.asyncio
async def test_external_redirect_is_skipped(fetcher: WebsiteFetcher) -> None:
    from backend.parser.html_parser import parse_html

    html = '<html><head><title>Home</title></head><body><h1>Home</h1><a href="/off-host">Leave</a></body></html>'
    payload = await crawl_site(
        scan_id="scan_ext",
        seed_url="https://example.com/",
        seed_fetch=_seed_fetch(html),
        seed_html=html,
        seed_html_data=parse_html(html),
        fetcher=fetcher,
        allowed_host="example.com",
        max_pages=10,
        max_depth=2,
    )
    off = next((item for item in payload.items if "off-host" in item.normalized_url), None)
    assert off is not None
    assert off.crawl_status == "skipped"
    assert off.skip_reason


def test_query_filters_and_sort() -> None:
    from backend.pages.ids import make_page_id
    from backend.pages.models import PageRecord

    scan_id = "scan_q"
    pages = [
        PageRecord(
            id=make_page_id(scan_id, "https://example.com/"),
            scan_id=scan_id,
            url="https://example.com/",
            normalized_url="https://example.com/",
            title="Home",
            h1="Homepage",
            page_type="homepage",
            crawl_status="crawled",
            http_status=200,
            indexable=True,
            issue_count=4,
            word_count=20,
        ),
        PageRecord(
            id=make_page_id(scan_id, "https://example.com/about"),
            scan_id=scan_id,
            url="https://example.com/about",
            normalized_url="https://example.com/about",
            title="About us",
            h1="About",
            page_type="about",
            crawl_status="crawled",
            http_status=200,
            indexable=None,
            issue_count=0,
            word_count=12,
        ),
        PageRecord(
            id=make_page_id(scan_id, "https://example.com/missing"),
            scan_id=scan_id,
            url="https://example.com/missing",
            normalized_url="https://example.com/missing",
            title="Not found",
            h1="404",
            page_type="unknown",
            crawl_status="crawled",
            http_status=404,
            indexable=False,
            issue_count=1,
            word_count=2,
        ),
        PageRecord(
            id=make_page_id(scan_id, "https://example.com/skip"),
            scan_id=scan_id,
            url="https://example.com/skip",
            normalized_url="https://example.com/skip",
            crawl_status="skipped",
            skip_reason="Maximum page limit reached.",
            issue_count=0,
        ),
    ]
    items, pagination = query_pages(pages, {"page_type": "about"})
    assert len(items) == 1
    assert items[0].page_type == "about"

    items, _ = query_pages(pages, {"crawl_status": "skipped"})
    assert len(items) == 1

    items, _ = query_pages(pages, {"http_status": "4xx"})
    assert len(items) == 1
    assert items[0].http_status == 404

    items, _ = query_pages(pages, {"indexable": "unknown"})
    assert {item.title for item in items} == {"About us", None}

    items, _ = query_pages(pages, {"has_issues": "true"})
    assert {item.issue_count for item in items} == {4, 1}

    items, pagination = query_pages(pages, {"search": "about", "page": 1, "page_size": 25})
    assert pagination["total"] == 1
    assert items[0].h1 == "About"

    items, pagination = query_pages(pages, {"sort": "issue_count", "order": "desc", "page_size": 2, "page": 1})
    assert items[0].issue_count >= items[1].issue_count
    assert pagination["page_size"] == 2
    assert pagination["pages"] == 2

    items, pagination = query_pages(pages, {"page_size": 1000})
    assert pagination["page_size"] == 100

    items, _ = query_pages(pages, {"search": "Homepage"})
    assert items[0].normalized_url == "https://example.com/"


def test_issue_attachment_uses_normalized_urls() -> None:
    from backend.issues.models import IssuesPayload, UnifiedIssue
    from backend.pages.ids import make_page_id
    from backend.pages.models import PageRecord

    scan_id = "scan_iss"
    page = PageRecord(
        id=make_page_id(scan_id, "https://example.com/about"),
        scan_id=scan_id,
        url="https://example.com/about/",
        normalized_url="https://example.com/about",
        crawl_status="crawled",
    )
    issues = IssuesPayload(
        issues=[
            UnifiedIssue(
                issue_id="issue_1",
                issue_key="seo:title",
                source="seo",
                analyzer="SEO",
                category="SEO",
                check_id="SEO-TITLE-001",
                title="Title too short",
                description="x",
                check_status="fail",
                severity="high",
                page_url="https://example.com/about/",
                pages=["https://example.com/about/#top"],
            )
        ]
    )
    attach_issues([page], issues)
    assert page.issue_count == 1
    assert page.severity_counts["high"] == 1
    assert page.related_issue_ids == ["issue_1"]
    assert normalize_page_url("https://example.com/about/") == page.normalized_url
