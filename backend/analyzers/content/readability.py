"""Deterministic English readability formulas. Not applied to unsupported languages."""

from __future__ import annotations

import re

from backend.analyzers.content.config import MIN_READABILITY_SENTENCES, MIN_READABILITY_WORDS
from backend.analyzers.content.models import ContentReadability

VOWELS = set("aeiouy")
WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
SENTENCE_RE = re.compile(r"[.!?]+")
SUPPORTED = {"en"}


def language_supported(language: str | None) -> bool:
    if not language:
        return False
    return language.lower().split("-", 1)[0] in SUPPORTED


def count_syllables(word: str) -> int:
    cleaned = re.sub(r"[^a-z]", "", word.lower())
    if not cleaned:
        return 0
    count = 0
    prev_vowel = False
    for char in cleaned:
        is_vowel = char in VOWELS
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if cleaned.endswith("e") and count > 1:
        count -= 1
    return max(count, 1)


def flesch_label(score: float) -> str:
    if score >= 90:
        return "Very easy"
    if score >= 70:
        return "Easy"
    if score >= 60:
        return "Standard"
    if score >= 30:
        return "Difficult"
    return "Very difficult"


def measure_readability(text: str, language: str | None) -> ContentReadability:
    if not language_supported(language):
        return ContentReadability(
            language=language,
            supported=False,
            reason="Readability formula not applied because the detected language is not supported.",
        )
    words = WORD_RE.findall(text or "")
    sentence_breaks = [part for part in SENTENCE_RE.split(text or "") if part.strip()]
    sentences = max(len(sentence_breaks), 1 if words else 0)
    if len(words) < MIN_READABILITY_WORDS or sentences < MIN_READABILITY_SENTENCES:
        return ContentReadability(
            language=language,
            supported=True,
            reason="Not enough complete English sentences were available to calculate a meaningful readability score.",
        )
    syllables = sum(count_syllables(word) for word in words)
    words_per_sentence = len(words) / sentences
    syllables_per_word = syllables / len(words)
    ease = 206.835 - (1.015 * words_per_sentence) - (84.6 * syllables_per_word)
    grade = (0.39 * words_per_sentence) + (11.8 * syllables_per_word) - 15.59
    ease = max(0.0, min(100.0, round(ease, 1)))
    grade = max(0.0, round(grade, 1))
    return ContentReadability(
        language=language,
        supported=True,
        flesch_reading_ease=ease,
        flesch_kincaid_grade=grade,
        label=flesch_label(ease),
    )
