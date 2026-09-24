from backend.analyzers.seo.checks.canonical import run as canonical
from backend.analyzers.seo.checks.headings import run as headings
from backend.analyzers.seo.checks.html import run as html
from backend.analyzers.seo.checks.images import run as images
from backend.analyzers.seo.checks.indexing import run as indexing
from backend.analyzers.seo.checks.links import run as links
from backend.analyzers.seo.checks.metadata import run as metadata
from backend.analyzers.seo.checks.robots import run as robots
from backend.analyzers.seo.checks.sitemap import run as sitemap
from backend.analyzers.seo.checks.social import run as social
from backend.analyzers.seo.checks.urls import run as urls

CHECK_RUNNERS = (
    metadata,
    headings,
    canonical,
    indexing,
    robots,
    sitemap,
    urls,
    images,
    links,
    social,
    html,
)

__all__ = ["CHECK_RUNNERS"]
