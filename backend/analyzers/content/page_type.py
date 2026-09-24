"""Conservative page-type classifier from URL, schema, and content signals."""

from __future__ import annotations

from urllib.parse import urlsplit

from backend.analyzers.content.extract import ExtractedPage
from backend.analyzers.content.models import ContentPageType, PageTypeName

PATH_HINTS: list[tuple[str, PageTypeName, float]] = [
    ("/contact", "contact", 0.72),
    ("/about", "about", 0.7),
    ("/login", "login", 0.78),
    ("/signin", "login", 0.74),
    ("/signup", "signup", 0.74),
    ("/register", "signup", 0.7),
    ("/search", "search", 0.7),
    ("/product", "product", 0.62),
    ("/pricing", "service", 0.55),
    ("/blog", "blog", 0.58),
    ("/article", "article", 0.6),
    ("/news", "article", 0.58),
    ("/post", "article", 0.55),
    ("/dashboard", "application", 0.7),
    ("/app/", "application", 0.55),
    ("/category", "listing", 0.55),
    ("/collection", "listing", 0.55),
]

SCHEMA_HINTS: dict[str, tuple[PageTypeName, float]] = {
    "Article": ("article", 0.82),
    "BlogPosting": ("blog", 0.84),
    "NewsArticle": ("article", 0.8),
    "Product": ("product", 0.8),
    "Service": ("service", 0.72),
    "FAQPage": ("article", 0.5),
}

TITLE_HINTS: list[tuple[str, PageTypeName, float]] = [
    ("contact", "contact", 0.55),
    ("about", "about", 0.5),
    ("log in", "login", 0.6),
    ("sign in", "login", 0.6),
    ("sign up", "signup", 0.58),
    ("search", "search", 0.45),
    ("pricing", "service", 0.4),
]


def classify_page(page: ExtractedPage) -> ContentPageType:
    scores: dict[PageTypeName, float] = {}
    reasons: dict[PageTypeName, list[str]] = {}

    def add(kind: PageTypeName, weight: float, reason: str) -> None:
        scores[kind] = scores.get(kind, 0.0) + weight
        reasons.setdefault(kind, []).append(reason)

    parsed = urlsplit(page.url)
    path = (parsed.path or "/").lower()
    if path in {"", "/", "/index.html", "/index.htm", "/home", "/home/"}:
        add("homepage", 0.55, "root path")
    for needle, kind, weight in PATH_HINTS:
        if needle in path:
            add(kind, weight, f"url contains {needle}")

    for schema in page.schema_types:
        hint = SCHEMA_HINTS.get(schema)
        if hint:
            add(hint[0], hint[1], f"schema {schema}")

    blob = " ".join(filter(None, [page.title, page.headings[0]["text"] if page.headings else ""])).lower()
    for needle, kind, weight in TITLE_HINTS:
        if needle in blob:
            add(kind, weight, f"title/heading mentions {needle}")

    if page.parsed.get("semantic", {}).get("article") and (page.dates or page.author_candidates):
        add("article", 0.45, "article landmark with date or author")
    if page.has_form and any("password" in (label or "").lower() for label in page.buttons):
        add("login", 0.5, "form with password-related controls")
    if page.has_form and page.word_count < 80 and "contact" in blob:
        add("contact", 0.35, "short form page")
    if page.word_count >= 400 and sum(1 for item in page.headings if item["level"] == 2) >= 2:
        add("article", 0.28, "long structured text")
    if page.image_count >= 4 and page.word_count < 80:
        add("listing", 0.2, "image-heavy short page")

    if not scores:
        return ContentPageType(type="unknown", confidence=0.2, reasons=["insufficient signals"])

    kind, score = max(scores.items(), key=lambda item: item[1])
    confidence = min(0.95, round(score, 2))
    if confidence < 0.45:
        return ContentPageType(type="unknown", confidence=confidence, reasons=reasons.get(kind, [])[:4])
    return ContentPageType(type=kind, confidence=confidence, reasons=reasons.get(kind, [])[:4])
