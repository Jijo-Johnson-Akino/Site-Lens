"""Configurable Trust & Credibility thresholds. Observable signals only."""

from __future__ import annotations

import os
import re


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


CLIENT_LOGO_MIN = _int_env("SITEBENCH_TRUST_CLIENT_LOGO_MIN", 3)
TESTIMONIAL_QUOTE_MIN = _int_env("SITEBENCH_TRUST_TESTIMONIAL_QUOTE_MIN", 1)
ARTICLE_FRESHNESS_YEARS = _int_env("SITEBENCH_TRUST_ARTICLE_FRESHNESS_YEARS", 3)
MAX_SIGNAL_ITEMS = _int_env("SITEBENCH_TRUST_MAX_SIGNAL_ITEMS", 40)

CATEGORY_WEIGHTS: dict[str, int] = {
    "identity": 15,
    "contact": 15,
    "transparency": 15,
    "policies": 10,
    "authorship": 10,
    "social_proof": 10,
    "business": 10,
    "credentials": 5,
    "security": 5,
    "consistency": 5,
}

CATEGORY_LABELS: dict[str, str] = {
    "identity": "Identity",
    "contact": "Contactability",
    "transparency": "Transparency",
    "policies": "Policies",
    "authorship": "Authorship",
    "social_proof": "Social Proof",
    "business": "Business Information",
    "credentials": "Credentials",
    "security": "Security Signals",
    "consistency": "Entity Consistency",
}

METHODOLOGY = (
    "Trust & Credibility analysis identifies observable signals presented by the website. "
    "It does not verify the truth, authenticity, legitimacy, legal compliance, or security of those claims."
)
CRAWL_NOTE = (
    "Absence of a detected signal does not prove that the underlying information does not exist "
    "outside the SiteLens crawl scope."
)
SCORE_NOTE = (
    "Trust Signals Score measures coverage of observable trust and credibility signals. "
    "It is not a legitimacy, fraud, safety, or legal-compliance score."
)
LIMITATIONS = [
    "SiteLens does not verify company registration, certifications, awards, testimonials, or payment accounts.",
    "SiteLens does not determine whether a company is trustworthy, legitimate, safe, or fraudulent.",
    "HTTPS describes the scanned URL scheme. It is not a security certification or vulnerability assessment.",
    "Policy and About detections are limited to pages and links observed within the crawl.",
    "Contact details are reported as published on the website and are not validated.",
]

SOCIAL_DOMAINS: dict[str, str] = {
    "linkedin.com": "LinkedIn",
    "www.linkedin.com": "LinkedIn",
    "twitter.com": "X",
    "www.twitter.com": "X",
    "x.com": "X",
    "www.x.com": "X",
    "facebook.com": "Facebook",
    "www.facebook.com": "Facebook",
    "instagram.com": "Instagram",
    "www.instagram.com": "Instagram",
    "youtube.com": "YouTube",
    "www.youtube.com": "YouTube",
    "youtu.be": "YouTube",
    "github.com": "GitHub",
    "www.github.com": "GitHub",
    "tiktok.com": "TikTok",
    "www.tiktok.com": "TikTok",
}

CONSUMER_EMAIL_DOMAINS = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "yahoo.com",
        "yahoo.co.uk",
        "hotmail.com",
        "outlook.com",
        "live.com",
        "icloud.com",
        "aol.com",
        "proton.me",
        "protonmail.com",
        "me.com",
        "msn.com",
    }
)

POLICY_HREF = {
    "privacy": re.compile(r"privacy", re.I),
    "terms": re.compile(r"terms|tos\b|terms-of-(service|use)|legal", re.I),
    "cookie": re.compile(r"cookie", re.I),
    "refund": re.compile(r"refund", re.I),
    "return": re.compile(r"return", re.I),
    "shipping": re.compile(r"shipping|delivery", re.I),
    "disclaimer": re.compile(r"disclaimer", re.I),
}

POLICY_TEXT = {
    "privacy": re.compile(r"\bprivacy\s*policy\b|\bprivacy\b", re.I),
    "terms": re.compile(r"\bterms(?:\s+and\s+conditions|\s+of\s+(?:service|use))?\b|\blegal\b", re.I),
    "cookie": re.compile(r"\bcookie\s*policy\b|\bcookies?\b", re.I),
    "refund": re.compile(r"\brefund(?:s|\s+policy)?\b", re.I),
    "return": re.compile(r"\breturn(?:s|\s+policy)?\b", re.I),
    "shipping": re.compile(r"\bshipping(?:\s+policy)?\b|\bdelivery\s+policy\b", re.I),
    "disclaimer": re.compile(r"\bdisclaimer\b", re.I),
}

POLICY_LABELS = {
    "privacy": "Privacy Policy",
    "terms": "Terms",
    "cookie": "Cookie Policy",
    "refund": "Refund Policy",
    "return": "Return Policy",
    "shipping": "Shipping Policy",
    "disclaimer": "Disclaimer",
}

ABOUT_HREF = re.compile(r"(about|about-us|who-we-are|our-story|company|team)", re.I)
ABOUT_TEXT = re.compile(r"\b(about us|about|who we are|our story|our company|the team|our team)\b", re.I)
CONTACT_HREF = re.compile(r"(contact|support|help-center|help|customer-service)", re.I)
CONTACT_TEXT = re.compile(r"\b(contact us|contact|support|help center|customer service|get in touch)\b", re.I)

TESTIMONIAL_HEADING = re.compile(
    r"\b(what our customers say|customer stories|testimonials?|reviews?|success stories|loved by)\b",
    re.I,
)
CLIENT_LOGO_HEADING = re.compile(
    r"\b(trusted by|our clients|our customers|our partners|partners|used by|as seen in|featured in)\b",
    re.I,
)
CASE_STUDY_RE = re.compile(r"\b(case stud(?:y|ies)|customer stor(?:y|ies)|success stor(?:y|ies))\b", re.I)
AWARD_RE = re.compile(r"\b(awards?|award-winning|winner)\b", re.I)
CERT_RE = re.compile(
    r"\b(certif(?:ied|ication|ications)|accredit(?:ed|ation)|licensed|memberships?|badges?)\b",
    re.I,
)
PAYMENT_RE = re.compile(
    r"\b(visa|mastercard|master card|paypal|stripe|razorpay|apple pay|google pay|amex|american express)\b",
    re.I,
)
SECURE_WORDING = re.compile(r"\b(secure checkout|ssl|https|encrypted|pci[\s-]?dss)\b", re.I)
HOURS_RE = re.compile(
    r"\b(opening hours|business hours|hours of operation|open(?:ing)?\s+hours|hours\s*:|mon(?:day)?[\s\-–]+fri(?:day)?)\b",
    re.I,
)
IDENTIFIER_RE = re.compile(
    r"\b(?:VAT|GST|EIN|ABN|ACN|CIN|Company\s*(?:No\.?|Number)|Registration\s*(?:No\.?|Number))[:\s#]*([A-Z0-9][A-Z0-9\-./]{3,})",
    re.I,
)
COPYRIGHT_RE = re.compile(r"(?:©|&copy;|copyright)\s*(?:©|&copy;)?\s*((?:19|20)\d{2})", re.I)
CITATION_RE = re.compile(r"\b(references|sources|citations|footnotes|methodology|editorial)\b", re.I)
USER_COUNT_RE = re.compile(r"\b(trusted by|used by|serving)\s+(\d[\d,]*)\+?\s+(companies|customers|clients|teams|businesses)\b", re.I)

PAYMENT_BRANDS = (
    "Visa",
    "Mastercard",
    "PayPal",
    "Stripe",
    "Razorpay",
    "Apple Pay",
    "Google Pay",
    "Amex",
)

ARTICLE_PAGE_TYPES = frozenset({"article", "blog"})
CONTACT_PAGE_TYPES = frozenset({"contact"})
ABOUT_PAGE_TYPES = frozenset({"about"})
COMMERCE_PAGE_TYPES = frozenset({"product", "pricing", "service"})
LOGIN_PAGE_TYPES = frozenset({"login", "signup"})
ORG_SCHEMA_TYPES = frozenset({"Organization", "Corporation", "LocalBusiness"})
ARTICLE_SCHEMA_TYPES = frozenset({"Article", "BlogPosting", "NewsArticle", "TechArticle"})
IDENTITY_SCHEMA_TYPES = ORG_SCHEMA_TYPES | {"Person", "WebSite"}
