"""Configurable content scoring, extraction limits, and thresholds."""

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


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


MAX_CONTENT_CHARS = _int_env("SITEBENCH_CONTENT_MAX_CHARS", 100_000)
MAX_WORDS = _int_env("SITEBENCH_CONTENT_MAX_WORDS", 20_000)
MAX_HEADINGS = _int_env("SITEBENCH_CONTENT_MAX_HEADINGS", 80)
MAX_PARAGRAPHS = _int_env("SITEBENCH_CONTENT_MAX_PARAGRAPHS", 200)
MAX_PAGES_FOR_DUPLICATE_COMPARISON = _int_env("SITEBENCH_CONTENT_MAX_DUP_PAGES", 20)
MAX_SIMILARITY_TEXT_LENGTH = _int_env("SITEBENCH_CONTENT_MAX_SIMILARITY_CHARS", 8_000)

THIN_WORDS = _int_env("SITEBENCH_CONTENT_THIN_WORDS", 100)
LOW_DEPTH_WORDS = _int_env("SITEBENCH_CONTENT_LOW_DEPTH_WORDS", 300)
LONG_PARAGRAPH_WORDS = _int_env("SITEBENCH_CONTENT_LONG_PARAGRAPH_WORDS", 180)
LONG_HEADING_CHARS = _int_env("SITEBENCH_CONTENT_LONG_HEADING_CHARS", 90)
NEAR_DUP = _float_env("SITEBENCH_CONTENT_NEAR_DUP", 0.85)
BOILERPLATE_WARN = _float_env("SITEBENCH_CONTENT_BOILERPLATE_WARN", 0.55)
REPEAT_RATIO_WARN = _float_env("SITEBENCH_CONTENT_REPEAT_RATIO_WARN", 0.12)
READ_DIFFICULT = _float_env("SITEBENCH_CONTENT_READ_DIFFICULT", 50)
READ_VERY_DIFFICULT = _float_env("SITEBENCH_CONTENT_READ_VERY_DIFFICULT", 30)
MIN_READABILITY_WORDS = _int_env("SITEBENCH_CONTENT_MIN_READ_WORDS", 80)
MIN_READABILITY_SENTENCES = _int_env("SITEBENCH_CONTENT_MIN_READ_SENTENCES", 3)

DEFAULT_CATEGORY_WEIGHTS: dict[str, float] = {
    "structure": 0.15,
    "depth": 0.15,
    "readability": 0.10,
    "headings": 0.10,
    "paragraphs": 0.05,
    "duplication": 0.15,
    "freshness": 0.05,
    "authorship": 0.05,
    "completeness": 0.10,
    "relationships": 0.05,
    "language": 0.05,
}

DEFAULT_CHECK_WEIGHTS: dict[str, int] = {
    "CONTENT-STRUCTURE-001": 10,
    "CONTENT-STRUCTURE-002": 6,
    "CONTENT-DEPTH-001": 12,
    "CONTENT-READ-001": 10,
    "CONTENT-HEAD-001": 5,
    "CONTENT-HEAD-002": 5,
    "CONTENT-HEAD-003": 4,
    "CONTENT-HEAD-004": 6,
    "CONTENT-PARA-001": 6,
    "CONTENT-PARA-002": 4,
    "CONTENT-LIST-001": 3,
    "CONTENT-DUP-001": 10,
    "CONTENT-REP-001": 8,
    "CONTENT-BOIL-001": 4,
    "CONTENT-FRESH-001": 5,
    "CONTENT-AUTH-001": 6,
    "CONTENT-COMP-001": 10,
    "CONTENT-LINK-001": 6,
    "CONTENT-LANG-001": 4,
    "CONTENT-CTA-001": 4,
}

LIMITATIONS = [
    "Automated analysis measures structural and statistical content signals; it does not judge factual accuracy, originality, usefulness, or editorial quality.",
    "Readability formulas provide statistical reading-level signals and do not judge the quality or accuracy of the content.",
    "Word count alone does not determine whether content is good.",
    "Site-wide duplicate analysis requires multiple crawled pages. This scan analyzes the primary page only unless extra pages were already collected.",
    "English readability formulas are not applied to unsupported languages.",
]


@dataclass(frozen=True)
class ContentScoringConfig:
    category_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_CATEGORY_WEIGHTS))
    check_weights: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_CHECK_WEIGHTS))
    thin_words: int = THIN_WORDS
    low_depth_words: int = LOW_DEPTH_WORDS
    long_paragraph_words: int = LONG_PARAGRAPH_WORDS
    long_heading_chars: int = LONG_HEADING_CHARS
    near_dup: float = NEAR_DUP
    boilerplate_warn: float = BOILERPLATE_WARN
    repeat_ratio_warn: float = REPEAT_RATIO_WARN
    read_difficult: float = READ_DIFFICULT
    read_very_difficult: float = READ_VERY_DIFFICULT
    min_readability_words: int = MIN_READABILITY_WORDS
    min_readability_sentences: int = MIN_READABILITY_SENTENCES
    max_content_chars: int = MAX_CONTENT_CHARS
    max_words: int = MAX_WORDS
    max_headings: int = MAX_HEADINGS
    max_paragraphs: int = MAX_PARAGRAPHS
    max_dup_pages: int = MAX_PAGES_FOR_DUPLICATE_COMPARISON
    max_similarity_chars: int = MAX_SIMILARITY_TEXT_LENGTH

    def weight_for(self, check_id: str) -> int:
        return self.check_weights.get(check_id, 1)


DEFAULT_SCORING = ContentScoringConfig()
