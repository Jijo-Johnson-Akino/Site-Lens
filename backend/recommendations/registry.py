"""Recommendation rule definitions and lookup."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecommendationRule:
    recommendation_key: str
    category: str
    title: str
    summary: str
    rationale: str
    action_steps: tuple[str, ...]
    trigger_issue_keys: tuple[str, ...]
    effort: str = "medium"
    impact: str = "medium"
    depends_on: tuple[str, ...] = ()
    priority_cap: str | None = None
    source_kind: str = "issues"


_RULES: list[RecommendationRule] = []
_BY_KEY: dict[str, RecommendationRule] = {}
_BY_ISSUE_KEY: dict[str, list[RecommendationRule]] = {}


def register(rule: RecommendationRule) -> RecommendationRule:
    if rule.recommendation_key in _BY_KEY:
        raise ValueError(f"duplicate recommendation_key: {rule.recommendation_key}")
    _RULES.append(rule)
    _BY_KEY[rule.recommendation_key] = rule
    for issue_key in rule.trigger_issue_keys:
        _BY_ISSUE_KEY.setdefault(issue_key, []).append(rule)
    return rule


def rule(
    recommendation_key: str,
    category: str,
    title: str,
    summary: str,
    rationale: str,
    action_steps: tuple[str, ...] | list[str],
    trigger_issue_keys: tuple[str, ...] | list[str],
    *,
    effort: str = "medium",
    impact: str = "medium",
    depends_on: tuple[str, ...] = (),
    priority_cap: str | None = None,
) -> RecommendationRule:
    return register(
        RecommendationRule(
            recommendation_key=recommendation_key,
            category=category,
            title=title,
            summary=summary,
            rationale=rationale,
            action_steps=tuple(action_steps),
            trigger_issue_keys=tuple(trigger_issue_keys),
            effort=effort,
            impact=impact,
            depends_on=depends_on,
            priority_cap=priority_cap,
        )
    )


def all_rules() -> tuple[RecommendationRule, ...]:
    from backend.recommendations.rules import load_rules

    load_rules()
    return tuple(_RULES)


def rule_by_key(recommendation_key: str) -> RecommendationRule | None:
    all_rules()
    return _BY_KEY.get(recommendation_key)


def rules_for_issue_key(issue_key: str) -> tuple[RecommendationRule, ...]:
    all_rules()
    return tuple(_BY_ISSUE_KEY.get(issue_key, ()))


def mapped_issue_keys() -> frozenset[str]:
    all_rules()
    return frozenset(_BY_ISSUE_KEY)
