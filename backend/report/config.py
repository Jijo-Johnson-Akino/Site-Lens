"""Report aggregation bounds and copy. Presentation only — no analysis checks."""

from __future__ import annotations

REPORT_VERSION = "1.0"

MAX_PRIORITY_ISSUES = 10
MAX_KEY_FINDINGS = 12
MAX_RECOMMENDATIONS = 8
MAX_AFFECTED_PAGES = 8
MAX_ANALYZER_ISSUES = 3
MAX_SCREENSHOTS = 3
MAX_INSIGHTS = 8
MAX_COMPETITOR_METRICS = 12

METHODOLOGY_PARAGRAPHS = (
    "SiteLens analyzes publicly accessible website content and behavior.",
    "Analysis is based on the pages and resources actually available during the scan.",
    "Scores are calculated from the SiteLens scoring methodology.",
    "Unavailable analyzers are not automatically scored as zero.",
    "Score coverage indicates how much of the configured scoring model was available.",
    "Automated analysis has limitations.",
    "Results are observations, not guarantees.",
)

AEO_NOTE = (
    "Observable signals related to answer-engine readability and content extractability. "
    "This is not a prediction that the site will rank in ChatGPT, Google AI Overviews, Gemini, or any other answer engine."
)
A11Y_LIMITATION = (
    "Automated accessibility analysis can identify many common issues but cannot establish "
    "full accessibility conformance or replace manual testing."
)
STRUCTURED_DATA_NOTE = "Detected structured-data signals. This is not a claim of eligibility for search rich results."
CRO_NOTE = (
    "Observable conversion-readiness signals and detected friction signals. "
    "SiteLens does not predict conversion rates or business outcomes."
)
TRUST_NOTE = (
    "Detected trust and credibility signals. SiteLens detects observable signals; "
    "it does not independently verify business claims, certifications, reviews, "
    "government registration, or social profiles."
)
ORPHAN_WORDING = "Potential orphan page based on the crawled internal-link graph."
COMPETITORS_EMPTY = "Competitor benchmarking was not included in this scan."
NO_ISSUES = "No issues were detected in the completed analysis."
NO_RECOMMENDATIONS = "No recommendations were generated from the available findings."
NO_SCREENSHOTS = "Visual captures were unavailable for this scan."
NO_ARCHITECTURE = "Architecture data is unavailable for this scan."
REPORT_UNAVAILABLE = "SiteLens could not assemble the report from the available scan results."

ANALYZER_SECTIONS = (
    ("seo", "SEO", "seo"),
    ("aeo", "AEO / AI Search Readiness", "aeo"),
    ("uiux", "UI/UX", "uiux"),
    ("accessibility", "Accessibility", "accessibility"),
    ("performance", "Performance", "performance"),
    ("content", "Content", "content"),
    ("structured_data", "Structured Data", "structured-data"),
    ("mobile", "Mobile", "mobile"),
    ("cro", "CRO", "cro"),
    ("trust", "Trust & Credibility", "trust"),
)

SAFE_SCREENSHOT_PREFIX = "/api/scans/"
