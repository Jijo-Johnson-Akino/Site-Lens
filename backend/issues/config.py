"""Configurable limits and labels for the unified issues engine.

Phase 12 only aggregates existing analyzer findings. It does not add checks.
"""

from __future__ import annotations

import os

MAX_ISSUES_PER_SCAN = int(os.getenv("SITEBENCH_MAX_ISSUES_PER_SCAN", "500"))
MAX_FINDINGS_PER_ANALYZER = int(os.getenv("SITEBENCH_MAX_FINDINGS_PER_ANALYZER", "200"))
MAX_PAGE_SIZE = int(os.getenv("SITEBENCH_MAX_ISSUE_PAGE_SIZE", "100"))
DEFAULT_PAGE_SIZE = int(os.getenv("SITEBENCH_DEFAULT_ISSUE_PAGE_SIZE", "25"))
MAX_SEARCH_LENGTH = int(os.getenv("SITEBENCH_MAX_ISSUE_SEARCH_LENGTH", "200"))
MAX_EVIDENCE_SIZE = int(os.getenv("SITEBENCH_MAX_EVIDENCE_SIZE", "4000"))

# Result payload keys used by existing analyzers (do not rename analyzers).
ANALYZER_SPECS: tuple[tuple[str, str, str, str], ...] = (
    ("seo", "SEO", "seo", "seo_error"),
    ("aeo", "AEO", "aeo", "aeo_error"),
    ("uiux", "UI/UX", "uiux", "uiux_error"),
    ("accessibility", "Accessibility", "accessibility", "accessibility_error"),
    ("performance", "Performance", "performance", "performance_error"),
    ("content", "Content", "content", "content_error"),
    ("structured_data", "Structured Data", "structured_data", "structured_data_error"),
    ("mobile", "Mobile", "mobile", "mobile_error"),
    ("cro", "CRO", "cro", "cro_error"),
    ("trust", "Trust", "trust", "trust_error"),
)

SOURCE_VALUES = tuple(item[0] for item in ANALYZER_SPECS)
CATEGORY_VALUES = tuple(item[1] for item in ANALYZER_SPECS)

SOURCE_TO_CATEGORY = {source: category for source, category, _payload, _error in ANALYZER_SPECS}
SOURCE_TO_PAYLOAD_KEY = {source: payload for source, _category, payload, _error in ANALYZER_SPECS}
SOURCE_TO_ERROR_KEY = {source: error for source, _category, _payload, error in ANALYZER_SPECS}

SOURCE_LABELS = {
    "seo": "SEO Analyzer",
    "aeo": "AEO Analyzer",
    "uiux": "UI/UX Analyzer",
    "accessibility": "Accessibility Analyzer",
    "performance": "Performance Analyzer",
    "content": "Content Analyzer",
    "structured_data": "Structured Data Analyzer",
    "mobile": "Mobile Analyzer",
    "cro": "CRO Analyzer",
    "trust": "Trust Analyzer",
    "unknown": "Unknown Analyzer",
}

SOURCE_HREF = {
    "seo": "seo",
    "aeo": "aeo",
    "uiux": "uiux",
    "accessibility": "accessibility",
    "performance": "performance",
    "content": "content",
    "structured_data": "structured-data",
    "mobile": "mobile",
    "cro": "cro",
    "trust": "trust",
}

SUBCATEGORY_LABELS = {
    "metadata": "Metadata",
    "indexability": "Indexability",
    "headings": "Headings",
    "canonical": "Canonical",
    "images": "Images",
    "links": "Links",
    "technical": "Technical",
    "social": "Social",
    "robots_sitemap": "Robots & Sitemap",
    "entity_understanding": "Entity",
    "organization_information": "Organization",
    "content_structure": "Content Structure",
    "extractability": "Extractability",
    "answers": "Answers",
    "faq": "FAQ",
    "author": "Authorship",
    "semantic": "Semantics",
    "ai_accessibility": "AI Accessibility",
    "structured_data": "Schema",
    "navigation": "Navigation",
    "layout": "Layout",
    "responsive": "Responsive",
    "typography": "Typography",
    "forms": "Forms",
    "javascript": "JavaScript",
    "caching": "Caching",
    "readability": "Readability",
    "schema": "Schema",
    "syntax": "Syntax",
    "overflow": "Overflow",
    "touch": "Touch",
    "viewport": "Viewport",
    "document": "Document",
    "landmarks": "Landmarks",
    "controls": "Controls",
    "aria": "ARIA",
    "keyboard": "Keyboard",
    "tables": "Tables",
    "media": "Media",
    "contrast": "Contrast",
    "structure": "Structure",
    "depth": "Depth",
    "paragraphs": "Paragraphs",
    "duplication": "Duplication",
    "freshness": "Freshness",
    "authorship": "Authorship",
    "completeness": "Completeness",
    "relationships": "Relationships",
    "detection": "Detection",
    "schema_types": "Schema Types",
    "identity": "Identity",
    "consistency": "Consistency",
    "properties": "Properties",
    "cta": "Calls to Action",
    "primary_cta": "Primary CTA",
    "cta_clarity": "CTA Clarity",
    "value_proposition": "Value Proposition",
    "conversion_path": "Conversion Path",
    "pricing": "Pricing / Offer",
    "contact": "Contact",
    "interaction": "Interaction Friction",
    "transparency": "Transparency",
    "policies": "Policies",
    "social_proof": "Social Proof",
    "credentials": "Credentials",
    "business": "Business Information",
    "security": "Security Signals",
    "spacing": "Spacing",
    "visibility": "Visibility",
    "overlays": "Overlays",
    "sticky": "Sticky Elements",
}

SEVERITIES = ("critical", "high", "medium", "low", "info")
PRIORITIES = ("critical", "high", "medium", "low")
CHECK_STATUSES = ("pass", "warning", "fail", "not_applicable", "info")
LIFECYCLE_STATUSES = ("open", "resolved", "ignored")
ACTIONABLE_STATUSES = frozenset({"fail", "warning"})

SORT_FIELDS = (
    "priority",
    "severity",
    "category",
    "affected_pages",
    "affected_elements",
    "created_at",
)
