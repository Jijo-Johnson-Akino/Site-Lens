"""Configurable structured-data scoring, limits, and type property rules."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


MAX_JSONLD_BLOCK_SIZE = _int_env("SITEBENCH_SCHEMA_MAX_BLOCK", 100_000)
MAX_SCHEMA_ENTITIES = _int_env("SITEBENCH_SCHEMA_MAX_ENTITIES", 80)
MAX_NESTING_DEPTH = _int_env("SITEBENCH_SCHEMA_MAX_DEPTH", 8)
MAX_PROPERTIES_PER_ENTITY = _int_env("SITEBENCH_SCHEMA_MAX_PROPS", 40)
MAX_FINDINGS = _int_env("SITEBENCH_SCHEMA_MAX_FINDINGS", 80)
MAX_SNIPPET_LENGTH = _int_env("SITEBENCH_SCHEMA_MAX_SNIPPET", 160)
MAX_PREVIEW_KEYS = _int_env("SITEBENCH_SCHEMA_MAX_PREVIEW_KEYS", 24)

KNOWN_TYPES = {
    "Organization",
    "Corporation",
    "LocalBusiness",
    "Person",
    "WebSite",
    "WebPage",
    "AboutPage",
    "ContactPage",
    "CollectionPage",
    "ItemPage",
    "Article",
    "BlogPosting",
    "NewsArticle",
    "Product",
    "Offer",
    "Service",
    "BreadcrumbList",
    "ListItem",
    "FAQPage",
    "Question",
    "Answer",
    "HowTo",
    "Event",
    "Review",
    "AggregateRating",
    "ImageObject",
    "VideoObject",
    "Brand",
    "PostalAddress",
    "ContactPoint",
    "Thing",
    "CreativeWork",
}

TYPE_PARENT = {
    "Corporation": "Organization",
    "LocalBusiness": "Organization",
    "BlogPosting": "Article",
    "NewsArticle": "Article",
    "AboutPage": "WebPage",
    "ContactPage": "WebPage",
    "CollectionPage": "WebPage",
    "ItemPage": "WebPage",
}

TYPE_RULES: dict[str, dict[str, tuple[str, ...]]] = {
    "Organization": {"core": ("name",), "recommended": ("url", "logo", "sameAs"), "useful": ("contactPoint", "address")},
    "Corporation": {"core": ("name",), "recommended": ("url", "logo", "sameAs"), "useful": ("contactPoint", "address")},
    "LocalBusiness": {"core": ("name",), "recommended": ("address", "telephone"), "useful": ("url", "openingHours")},
    "Person": {"core": ("name",), "recommended": ("url", "sameAs", "image"), "useful": ()},
    "WebSite": {"core": ("name", "url"), "recommended": ("publisher", "description"), "useful": ()},
    "WebPage": {"core": ("name",), "recommended": ("url", "publisher"), "useful": ("description",)},
    "AboutPage": {"core": ("name",), "recommended": ("url",), "useful": ()},
    "ContactPage": {"core": ("name",), "recommended": ("url",), "useful": ()},
    "Article": {"core": ("headline",), "recommended": ("author", "datePublished", "image"), "useful": ("dateModified",)},
    "BlogPosting": {"core": ("headline",), "recommended": ("author", "datePublished", "image"), "useful": ("dateModified",)},
    "NewsArticle": {"core": ("headline",), "recommended": ("author", "datePublished", "image"), "useful": ("dateModified",)},
    "Product": {"core": ("name",), "recommended": ("description", "image", "brand", "offers"), "useful": ("sku",)},
    "Offer": {"core": (), "recommended": ("price", "priceCurrency", "availability"), "useful": ()},
    "Service": {"core": ("name",), "recommended": ("description",), "useful": ("provider",)},
    "BreadcrumbList": {"core": ("itemListElement",), "recommended": (), "useful": ()},
    "FAQPage": {"core": (), "recommended": ("mainEntity",), "useful": ()},
    "Event": {"core": ("name",), "recommended": ("startDate", "location"), "useful": ("organizer",)},
    "Review": {"core": (), "recommended": ("reviewRating", "author"), "useful": ()},
}

PAGE_TYPE_HINTS: dict[str, tuple[str, ...]] = {
    "homepage": ("WebSite", "Organization", "WebPage"),
    "article": ("Article", "BlogPosting", "NewsArticle"),
    "blog": ("BlogPosting", "Article"),
    "product": ("Product", "Offer"),
    "service": ("Service",),
    "contact": ("ContactPage", "Organization", "LocalBusiness"),
    "about": ("AboutPage", "Organization"),
}

DEFAULT_CATEGORY_WEIGHTS: dict[str, float] = {
    "detection": 0.10,
    "syntax": 0.20,
    "schema_types": 0.10,
    "identity": 0.10,
    "properties": 0.15,
    "relationships": 0.10,
    "urls": 0.05,
    "consistency": 0.10,
    "alignment": 0.05,
    "social": 0.05,
}

DEFAULT_CHECK_WEIGHTS: dict[str, int] = {
    "SCHEMA-DETECT-001": 8,
    "SCHEMA-DETECT-002": 4,
    "SCHEMA-DETECT-003": 3,
    "SCHEMA-SYNTAX-001": 16,
    "SCHEMA-CONTEXT-001": 6,
    "SCHEMA-TYPE-001": 4,
    "SCHEMA-TYPE-002": 3,
    "SCHEMA-ID-001": 8,
    "SCHEMA-ID-002": 12,
    "SCHEMA-ID-003": 2,
    "SCHEMA-ID-004": 5,
    "SCHEMA-REL-001": 8,
    "SCHEMA-URL-001": 5,
    "SCHEMA-SAMEAS-001": 4,
    "SCHEMA-ORG-001": 10,
    "SCHEMA-ARTICLE-001": 8,
    "SCHEMA-PRODUCT-001": 10,
    "SCHEMA-OFFER-001": 8,
    "SCHEMA-CORE-001": 10,
    "SCHEMA-REC-001": 3,
    "SCHEMA-CONSIST-001": 6,
    "SCHEMA-CONSIST-002": 5,
    "SCHEMA-CONSIST-003": 5,
    "SCHEMA-CONSIST-004": 5,
    "SCHEMA-OG-001": 4,
    "SCHEMA-TW-001": 3,
}

LIMITATIONS = [
    "Structured data analysis measures markup that is present on the page. It does not prove search-engine eligibility, rich results, rankings, or AI citations.",
    "SiteLens does not fetch schema.org, sameAs, image, or logo URLs. URL checks are format-only.",
    "Open Graph and Twitter/X tags are social metadata, not Schema.org structured data.",
    "Missing schema types are reported only when they appear relevant to the observed page type. Absence of schema is not an automatic failure.",
    "Property rules are SiteLens analysis heuristics, not a full Schema.org specification copy.",
]


@dataclass(frozen=True)
class SchemaScoringConfig:
    category_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_CATEGORY_WEIGHTS))
    check_weights: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_CHECK_WEIGHTS))
    max_block_size: int = MAX_JSONLD_BLOCK_SIZE
    max_entities: int = MAX_SCHEMA_ENTITIES
    max_depth: int = MAX_NESTING_DEPTH
    max_properties: int = MAX_PROPERTIES_PER_ENTITY
    max_findings: int = MAX_FINDINGS
    max_snippet: int = MAX_SNIPPET_LENGTH
    max_preview_keys: int = MAX_PREVIEW_KEYS

    def weight_for(self, check_id: str) -> int:
        return self.check_weights.get(check_id, 1)


DEFAULT_SCORING = SchemaScoringConfig()
