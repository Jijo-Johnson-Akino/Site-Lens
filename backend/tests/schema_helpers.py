from __future__ import annotations

from backend.analyzers.structured_data.analyzer import analyze_structured_data
from backend.analyzers.structured_data.context import StructuredDataContext
from backend.analyzers.structured_data.models import SchemaResult
from backend.parser.html_parser import parse_html


def wrap(body: str, extra_head: str = "") -> str:
    return f"""<!doctype html><html lang="en"><head>
<title>Example Company</title>
<meta name="description" content="Example Company builds website quality measurements.">
{extra_head}
</head><body>
<h1>Example Company</h1>
{body}
</body></html>"""


def jsonld(payload: str) -> str:
    return f'<script type="application/ld+json">{payload}</script>'


def analyze_html(html: str, url: str = "https://example.com/") -> SchemaResult:
    return analyze_structured_data(
        StructuredDataContext(
            page_url=url,
            final_url=url,
            html=parse_html(html),
            html_source=html,
        )
    )


def by_id(result: SchemaResult, check_id: str):
    return next(check for check in result.checks if check.check_id == check_id)


ORG = '{"@context":"https://schema.org","@type":"Organization","@id":"https://example.com/#org","name":"Example Company","url":"https://example.com/","logo":"https://example.com/logo.png","sameAs":["https://example.com/about"]}'
WEBSITE = '{"@context":"https://schema.org","@graph":[{"@type":"WebSite","@id":"https://example.com/#website","name":"Example Company","url":"https://example.com/","publisher":{"@id":"https://example.com/#org"}},{"@type":"WebPage","@id":"https://example.com/#webpage","name":"Example Company","url":"https://example.com/","isPartOf":{"@id":"https://example.com/#website"}}]}'
ARTICLE = '{"@context":"https://schema.org","@type":"Article","headline":"How measurements work","author":{"@type":"Person","name":"Ada Example"},"datePublished":"2024-04-12","image":"https://example.com/a.jpg"}'
PRODUCT = '{"@context":"https://schema.org","@type":"Product","name":"Analytics Widget","description":"A widget","image":"https://example.com/p.png","brand":{"@type":"Brand","name":"Example"},"offers":{"@type":"Offer","price":"12.00","priceCurrency":"USD","availability":"https://schema.org/InStock"}}'
GRAPH = '{"@context":"https://schema.org","@graph":[{"@type":"Organization","@id":"#org","name":"Example Company"},{"@type":"WebPage","name":"Example Company","publisher":{"@id":"#org"}}]}'
UNKNOWN = '{"@context":"https://schema.org","@type":"CustomType","name":"Mystery"}'
NO_CONTEXT = '{"@type":"Organization","name":"Example Company","url":"https://example.com/"}'
DUP = '{"@context":"https://schema.org","@graph":[{"@type":"Organization","@id":"https://example.com/#org","name":"Example Company"},{"@type":"Organization","@id":"https://example.com/#org","name":"Example Company"}]}'
CONFLICT = '{"@context":"https://schema.org","@graph":[{"@type":"Organization","@id":"https://example.com/#org","name":"ABC Company"},{"@type":"Organization","@id":"https://example.com/#org","name":"XYZ Company"}]}'
BROKEN = '{"@context":"https://schema.org","@type":"WebPage","name":"Example Company","publisher":{"@id":"#missing-organization"}}'
MISMATCH = '{"@context":"https://schema.org","@type":"Organization","name":"Completely Different Company"}'
MICRO = '<div itemscope itemtype="https://schema.org/Organization"><span itemprop="name">Example Company</span><a itemprop="url" href="https://example.com/">Home</a></div>'
RDFA = '<div typeof="Organization"><span property="name">Example Company</span></div>'
OG = '<meta property="og:title" content="Example Company"><meta property="og:description" content="Hello"><meta property="og:image" content="https://example.com/og.png"><meta property="og:url" content="https://example.com/"><meta property="og:type" content="website"><meta property="og:site_name" content="Example">'
TW = '<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="Example Company"><meta name="twitter:description" content="Hello"><meta name="twitter:image" content="https://example.com/tw.png">'
