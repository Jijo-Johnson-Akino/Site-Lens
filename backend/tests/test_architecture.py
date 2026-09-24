from __future__ import annotations

import httpx
import pytest

from backend.architecture.engine import build_architecture, depth_distribution, page_type_distribution, summary_from_graph
from backend.architecture.query import parse_graph_limit, query_links, query_nodes, select_graph_nodes
from backend.pages.crawler import crawl_site
from backend.pages.discover import extract_internal_link_edges, resolve_internal_candidates
from backend.pages.ids import make_link_id, make_page_id
from backend.pages.models import InternalLink, PageRecord, PagesPayload
from backend.parser.html_parser import parse_html
from backend.services.url_identity import normalize_page_url, url_path, url_path_depth
from backend.services.url_validator import UrlValidator
from backend.services.website_fetcher import WebsiteFetcher

WORDS = "content " * 80

HOME = f"""<!doctype html><html lang="en"><head><title>Homepage</title>
<link rel="canonical" href="https://example.com/">
</head><body>
<h1>Homepage</h1>
<p>Welcome to the architecture fixture site used for SiteBench tests. {WORDS}</p>
<a href="/about">About</a>
<a href="/services">Services</a>
<a href="/blog">Blog</a>
<a href="/contact">Contact</a>
<a href="/about">About</a>
<a href="https://other.example/offsite">Offsite</a>
<a href="/logo.png">Logo</a>
<a href="mailto:hi@example.com">Email</a>
</body></html>"""

ABOUT = f"""<!doctype html><html><head><title>About us</title></head>
<body><h1>About</h1><p>About the company with enough words. {WORDS}</p>
<a href="/">Home</a></body></html>"""

SERVICES = """<!doctype html><html><head><title>Services</title>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Service","name":"Services"}</script>
</head><body><h1>Services</h1><p>Our services.</p>
<a href="/services/web-development">Web Development</a>
<a href="/services/design">Design</a>
<a href="/">Home</a>
</body></html>"""

WEBDEV = """<!doctype html><html><head><title>Web Development</title>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Service","name":"Web Development"}</script>
</head><body><h1>Web Development</h1><p>Implementation work.</p>
<a href="/services">Services</a>
<a href="/services/design">Design</a>
</body></html>"""

DESIGN = """<!doctype html><html><head><title>Design</title>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Service","name":"Design"}</script>
</head><body><h1>Design</h1><p>Visual design service page with no further internal pages.</p>
</body></html>"""

BLOG = """<!doctype html><html><head><title>Blog</title></head>
<body><h1>Blog</h1><p>Listing of articles.</p>
<a href="/blog/article-1">Article 1</a>
<a href="/blog/article-2">Article 2</a>
</body></html>"""

ARTICLE1 = f"""<!doctype html><html><head><title>Article 1</title>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"Article","headline":"Article 1"}}</script>
</head><body><article><h1>Article 1</h1><h2>One</h2><p>{WORDS}</p>
<h2>Two</h2><p>More words for the classifier.</p>
<a href="/services">Services</a>
<a href="/blog">Blog</a>
</article></body></html>"""

ARTICLE2 = f"""<!doctype html><html><head><title>Article 2</title>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"Article","headline":"Article 2"}}</script>
</head><body><article><h1>Article 2</h1><h2>One</h2><p>{WORDS}</p>
<h2>Two</h2><p>More words for the classifier.</p>
<a href="/blog">Blog</a>
</article></body></html>"""

CONTACT = """<!doctype html><html><head><title>Contact</title></head>
<body><h1>Contact</h1><form><label>Email</label><input type="email"></form>
<p>Reach the team through this contact page.</p></body></html>"""

LOGIN = """<!doctype html><html><head><title>Sign in</title></head>
<body><h1>Sign in</h1><form><label>Password</label><input type="password"></form>
<p>Account access.</p></body></html>"""

ORPHAN = f"""<!doctype html><html><head><title>Unlinked page</title></head>
<body><h1>Unlinked page</h1><p>Only listed in the sitemap. {WORDS}</p></body></html>"""

SITEMAP = """<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://example.com/orphan</loc></url>
<url><loc>https://example.com/login</loc></url>
</urlset>"""

PAGES = {
    "/": HOME,
    "/about": ABOUT,
    "/services": SERVICES,
    "/services/web-development": WEBDEV,
    "/services/design": DESIGN,
    "/blog": BLOG,
    "/blog/article-1": ARTICLE1,
    "/blog/article-2": ARTICLE2,
    "/contact": CONTACT,
    "/login": LOGIN,
    "/orphan": ORPHAN,
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
    body = PAGES.get(path)
    if body is None:
        return httpx.Response(404, text="missing", headers={"content-type": "text/html"})
    return httpx.Response(200, text=body, headers={"content-type": "text/html"})


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


async def _crawl(fetcher: WebsiteFetcher, scan_id: str = "scan_arch") -> PagesPayload:
    return await crawl_site(
        scan_id=scan_id,
        seed_url="https://example.com/",
        seed_fetch=_seed_fetch(HOME),
        seed_html=HOME,
        seed_html_data=parse_html(HOME),
        fetcher=fetcher,
        allowed_host="example.com",
        sitemap_body=SITEMAP,
        max_pages=50,
        max_depth=3,
    )


def _page(scan_id: str, url: str, **overrides) -> PageRecord:
    normalized = normalize_page_url(url)
    data = {
        "id": make_page_id(scan_id, normalized),
        "scan_id": scan_id,
        "url": url,
        "normalized_url": normalized,
        "crawl_status": "crawled",
        "depth": 0,
        "is_seed": False,
    }
    data.update(overrides)
    return PageRecord.model_validate(data)


def test_relative_url_resolution_and_same_origin() -> None:
    html = parse_html('<a href="../design">Design</a><a href="/about">About</a><a href="#top">Top</a>')
    edges = extract_internal_link_edges(
        html,
        base_url="https://example.com/services/web-development/",
        seed_url="https://example.com/",
    )
    dests = {item["destination_url"] for item in edges}
    assert "https://example.com/services/design" in dests
    assert "https://example.com/about" in dests
    assert all(item["destination_url"] != "https://example.com/services/web-development" for item in edges)


def test_external_and_resource_urls_excluded() -> None:
    html = parse_html(
        '<a href="https://other.example/x">Off</a><a href="/logo.png">Img</a>'
        '<a href="mailto:hi@example.com">Mail</a><a href="/about">About</a>'
    )
    edges = extract_internal_link_edges(html, base_url="https://example.com/", seed_url="https://example.com/")
    dests = [item["destination_url"] for item in edges]
    assert dests == ["https://example.com/about"]
    internal, external = resolve_internal_candidates(
        ["https://other.example/x", "/about"],
        base_url="https://example.com/",
        seed_url="https://example.com/",
    )
    assert normalize_page_url(internal[0]) == "https://example.com/about"
    assert external


def test_url_normalization_and_path_depth() -> None:
    assert normalize_page_url("https://EXAMPLE.com/about/#team") == "https://example.com/about"
    assert url_path("https://example.com/services/web-development/") == "/services/web-development"
    assert url_path_depth("https://example.com/services/web-development/") == 2
    assert url_path_depth("https://example.com/") == 0
    assert url_path_depth("https://example.com/about") == 1


def test_duplicate_link_identity() -> None:
    scan_id = "scan_dup"
    source = make_page_id(scan_id, "https://example.com/")
    dest = make_page_id(scan_id, "https://example.com/about")
    first = make_link_id(scan_id, source, dest, "About")
    second = make_link_id(scan_id, source, dest, "About")
    third = make_link_id(scan_id, source, dest, "Learn more")
    assert first == second
    assert first != third


def test_orphan_terminal_and_counts() -> None:
    scan_id = "scan_graph"
    home = _page(scan_id, "https://example.com/", is_seed=True, title="Home", page_type="homepage", depth=0)
    about = _page(scan_id, "https://example.com/about", title="About", page_type="about", depth=1)
    contact = _page(scan_id, "https://example.com/contact", title="Contact", page_type="contact", depth=1)
    orphan = _page(scan_id, "https://example.com/orphan", title="Orphan", page_type="unknown", depth=1)
    design = _page(scan_id, "https://example.com/design", title="Design", page_type="service", depth=2)
    links = [
        InternalLink(
            id="l1",
            scan_id=scan_id,
            source_page_id=home.id,
            destination_page_id=about.id,
            source_url=home.normalized_url,
            destination_url=about.normalized_url,
            anchor_text="About",
        ),
        InternalLink(
            id="l2",
            scan_id=scan_id,
            source_page_id=home.id,
            destination_page_id=contact.id,
            source_url=home.normalized_url,
            destination_url=contact.normalized_url,
            anchor_text="Contact",
        ),
        InternalLink(
            id="l3",
            scan_id=scan_id,
            source_page_id=about.id,
            destination_page_id=home.id,
            source_url=about.normalized_url,
            destination_url=home.normalized_url,
            anchor_text="Home",
        ),
    ]
    graph = build_architecture(
        PagesPayload(items=[home, about, contact, orphan, design], internal_links=links)
    )
    assert set(graph.nodes) == {home.id, about.id, contact.id, orphan.id, design.id}
    assert graph.nodes[about.id].inbound_count == 1
    assert graph.nodes[home.id].outbound_count == 2
    assert graph.nodes[about.id].outbound_count == 1
    assert graph.nodes[orphan.id].potential_orphan is True
    assert graph.nodes[home.id].potential_orphan is False
    assert graph.nodes[contact.id].terminal_page is True
    assert graph.nodes[contact.id].dead_end is False
    assert graph.nodes[design.id].dead_end is True
    assert graph.nodes[orphan.id].dead_end is True
    summary = summary_from_graph(graph)
    assert summary["page_count"] == 5
    assert summary["internal_link_count"] == 3
    assert summary["potential_orphan_count"] == 2
    assert summary["dead_end_count"] == 2
    assert summary["terminal_page_count"] == 1
    assert summary["max_crawl_depth"] == 2
    assert "architecture_score" not in summary
    depths = {row["depth"]: row["page_count"] for row in depth_distribution(graph)}
    assert depths[0] == 1
    assert depths[1] == 3
    types = {row["page_type"]: row["page_count"] for row in page_type_distribution(graph)}
    assert types["homepage"] == 1
    assert types["contact"] == 1


def test_scan_isolation_skips_foreign_links() -> None:
    scan_id = "scan_own"
    home = _page(scan_id, "https://example.com/", is_seed=True, depth=0)
    about = _page(scan_id, "https://example.com/about", depth=1)
    foreign = InternalLink(
        id="lf",
        scan_id="scan_other",
        source_page_id=home.id,
        destination_page_id=about.id,
        source_url=home.normalized_url,
        destination_url=about.normalized_url,
        anchor_text="About",
    )
    graph = build_architecture(PagesPayload(items=[home, about], internal_links=[foreign]))
    assert graph.links == []
    assert graph.nodes[about.id].inbound_count == 0


def test_filtering_search_pagination_and_graph_limit() -> None:
    scan_id = "scan_q"
    pages = [_page(scan_id, f"https://example.com/p{index}", title=f"Page {index}", depth=index, page_type="unknown") for index in range(8)]
    pages[0].is_seed = True
    pages[0].page_type = "homepage"
    pages[3].issue_count = 2
    links = [
        InternalLink(
            id=f"l{index}",
            scan_id=scan_id,
            source_page_id=pages[0].id,
            destination_page_id=pages[index].id,
            source_url=pages[0].normalized_url,
            destination_url=pages[index].normalized_url,
            anchor_text=f"Go {index}",
        )
        for index in range(1, 6)
    ]
    graph = build_architecture(PagesPayload(items=pages, internal_links=links))
    matching, paged, pagination = query_nodes(graph, {"search": "Page 3", "page": 1, "page_size": 10})
    assert pagination["total"] == 1
    assert paged[0].page.title == "Page 3"
    _, issues, _ = query_nodes(graph, {"has_issues": "true"})
    assert len(issues) == 1
    _, depth1, _ = query_nodes(graph, {"depth": "1"})
    assert all(node.page.depth == 1 for node in depth1)
    orphans, _, _ = query_nodes(graph, {"orphan": "true", "page_size": 50})
    assert all(node.potential_orphan for node in orphans)
    selected = select_graph_nodes(list(graph.nodes.values()), limit=3, focus_page_id=pages[7].id)
    assert len(selected) == 3
    assert pages[0].id in {node.page.id for node in selected}
    assert pages[7].id in {node.page.id for node in selected}
    assert parse_graph_limit("1000") == 100
    items, link_page = query_links(graph, {"search": "Go 2", "page_size": 25})
    assert link_page["total"] == 1
    assert items[0].anchor_text == "Go 2"
    oversized, over_page = query_links(graph, {"page_size": 1000})
    assert over_page["page_size"] == 100
    assert len(oversized) <= 100


@pytest.mark.asyncio
async def test_architecture_fixture_crawl(fetcher: WebsiteFetcher) -> None:
    payload = await _crawl(fetcher)
    graph = build_architecture(payload)
    by_url = {node.page.normalized_url: node for node in graph.nodes.values()}
    assert "https://example.com/" in by_url
    assert "https://example.com/about" in by_url
    assert "https://example.com/services" in by_url
    assert "https://example.com/services/web-development" in by_url
    assert "https://example.com/services/design" in by_url
    assert "https://example.com/blog" in by_url
    assert "https://example.com/blog/article-1" in by_url
    assert "https://example.com/blog/article-2" in by_url
    assert "https://example.com/contact" in by_url
    assert "https://example.com/orphan" in by_url
    assert not any(url.endswith(".png") for url in by_url)
    assert all("other.example" not in url for url in by_url)

    home = by_url["https://example.com/"]
    about = by_url["https://example.com/about"]
    services = by_url["https://example.com/services"]
    webdev = by_url["https://example.com/services/web-development"]
    design = by_url["https://example.com/services/design"]
    blog = by_url["https://example.com/blog"]
    article1 = by_url["https://example.com/blog/article-1"]
    contact = by_url["https://example.com/contact"]
    orphan = by_url["https://example.com/orphan"]
    login = by_url["https://example.com/login"]

    assert home.page.depth == 0
    assert about.page.depth == 1
    assert webdev.page.depth == 2
    assert article1.page.depth == 2
    assert url_path_depth(webdev.page.normalized_url) == 2
    assert webdev.page.depth != url_path_depth(webdev.page.normalized_url) or webdev.page.depth == 2

    dests_from_home = {link.destination_url for link in home.outbound}
    assert dests_from_home >= {
        "https://example.com/about",
        "https://example.com/services",
        "https://example.com/blog",
        "https://example.com/contact",
    }
    assert "https://other.example/offsite" not in dests_from_home
    about_from_home = [link for link in home.outbound if link.destination_url == "https://example.com/about"]
    assert len(about_from_home) == 1

    assert about.inbound_count >= 1
    assert services.inbound_count >= 2
    assert design.inbound_count >= 2
    assert article1.inbound_count == 1
    assert orphan.inbound_count == 0
    assert orphan.potential_orphan is True
    assert home.potential_orphan is False
    assert contact.terminal_page is True
    assert contact.dead_end is False
    assert design.outbound_count == 0
    assert design.dead_end is True
    assert login.potential_orphan is True
    assert login.terminal_page is True

    pairs = {(link.source_url, link.destination_url) for link in graph.links}
    assert ("https://example.com/", "https://example.com/about") in pairs
    assert ("https://example.com/services", "https://example.com/services/web-development") in pairs
    assert ("https://example.com/services/web-development", "https://example.com/services/design") in pairs
    assert ("https://example.com/blog", "https://example.com/blog/article-1") in pairs
    assert ("https://example.com/blog/article-1", "https://example.com/services") in pairs

    summary = summary_from_graph(graph)
    assert summary["page_count"] >= 11
    assert summary["internal_link_count"] >= 10
    assert summary["potential_orphan_count"] >= 2
    assert payload.summary.external_links_discovered >= 1
