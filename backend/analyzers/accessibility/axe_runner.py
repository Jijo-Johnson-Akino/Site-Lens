"""Inject axe-core into a Playwright page and normalize rule results."""

from __future__ import annotations

import logging
import re
from typing import Any

from backend.analyzers.accessibility.config import AXE_BUNDLE, AXE_TAGS, AXE_TIMEOUT_MS, IMPACT_SEVERITY
from backend.analyzers.accessibility.models import CheckGroup, CheckResult, make_check
from backend.analyzers.uiux.sanitizer import sanitize_selector, sanitize_text
from backend.errors import ScanError

logger = logging.getLogger("sitebench.a11y")

AXE_CHECK_MAP: dict[str, tuple[str, CheckGroup, str]] = {
    "html-has-lang": ("A11Y-DOC-001", "document", "HTML lang attribute exists"),
    "html-lang-valid": ("A11Y-DOC-003", "document", "Document language is valid"),
    "document-title": ("A11Y-DOC-002", "document", "Document title exists"),
    "landmark-one-main": ("A11Y-LAND-001", "landmarks", "Main landmark exists"),
    "landmark-no-duplicate-main": ("A11Y-LAND-002", "landmarks", "A single main landmark"),
    "landmark-unique": ("A11Y-LAND-003", "landmarks", "Landmarks have distinguishable names"),
    "bypass": ("A11Y-LAND-004", "landmarks", "Skip navigation mechanism"),
    "empty-heading": ("A11Y-HEAD-002", "headings", "Headings have accessible text"),
    "heading-order": ("A11Y-HEAD-003", "headings", "Heading hierarchy"),
    "image-alt": ("A11Y-IMG-001", "images", "Images have alternative text"),
    "input-image-alt": ("A11Y-IMG-003", "images", "Image inputs have accessible names"),
    "link-name": ("A11Y-LINK-001", "links", "Links have accessible names"),
    "button-name": ("A11Y-CTRL-001", "controls", "Buttons have accessible names"),
    "input-button-name": ("A11Y-CTRL-001", "controls", "Buttons have accessible names"),
    "label": ("A11Y-FORM-001", "forms", "Form controls have accessible names"),
    "select-name": ("A11Y-FORM-001", "forms", "Form controls have accessible names"),
    "label-title-only": ("A11Y-FORM-001", "forms", "Form controls have accessible names"),
    "aria-valid-attr": ("A11Y-ARIA-001", "aria", "ARIA attributes are valid"),
    "aria-valid-attr-value": ("A11Y-ARIA-001", "aria", "ARIA attributes are valid"),
    "aria-allowed-attr": ("A11Y-ARIA-001", "aria", "ARIA attributes are valid"),
    "aria-roles": ("A11Y-ARIA-001", "aria", "ARIA attributes are valid"),
    "aria-allowed-role": ("A11Y-ARIA-001", "aria", "ARIA attributes are valid"),
    "aria-required-attr": ("A11Y-ARIA-001", "aria", "ARIA attributes are valid"),
    "aria-command-name": ("A11Y-CTRL-001", "controls", "Buttons have accessible names"),
    "aria-hidden-focus": ("A11Y-ARIA-003", "aria", "Hidden content is not focusable"),
    "duplicate-id": ("A11Y-ID-001", "aria", "IDs are unique"),
    "duplicate-id-active": ("A11Y-ID-001", "aria", "IDs are unique"),
    "duplicate-id-aria": ("A11Y-ID-001", "aria", "IDs are unique"),
    "frame-title": ("A11Y-IFRAME-001", "other", "Iframes have accessible names"),
    "color-contrast": ("A11Y-CONTRAST-001", "contrast", "Text has sufficient color contrast"),
    "color-contrast-enhanced": ("A11Y-CONTRAST-001", "contrast", "Text has sufficient color contrast"),
    "td-headers-attr": ("A11Y-TABLE-001", "tables", "Data tables expose headers"),
    "th-has-data-cells": ("A11Y-TABLE-001", "tables", "Data tables expose headers"),
    "tabindex": ("A11Y-FOCUS-001", "keyboard", "tabindex values are not positive"),
    "meta-viewport": ("A11Y-VIEW-001", "other", "Viewport allows user scaling"),
    "video-caption": ("A11Y-MEDIA-002", "media", "Video caption track"),
}

WCAG_TAG = re.compile(r"^wcag(\d)(\d)(\d+)$", re.I)

AXE_RUN_JS = """async (tags) => {
  const result = await axe.run({
    runOnly: { type: "tag", values: tags },
    resultTypes: ["violations", "incomplete", "passes", "inapplicable"]
  });
  const slim = (items) => (items || []).slice(0, 60).map((item) => ({
    id: item.id,
    impact: item.impact,
    description: item.description,
    help: item.help,
    helpUrl: item.helpUrl,
    tags: item.tags,
    nodes: (item.nodes || []).slice(0, 8).map((node) => ({
      target: (node.target || []).slice(0, 2),
      html: String(node.html || "").slice(0, 180),
      failureSummary: String(node.failureSummary || "").slice(0, 240)
    }))
  }));
  return {
    violations: slim(result.violations),
    incomplete: slim(result.incomplete),
    passes: (result.passes || []).map((item) => item.id),
    inapplicable: (result.inapplicable || []).map((item) => item.id),
    version: (typeof axe !== "undefined" && axe.version) || (result.testEngine && result.testEngine.version) || null
  };
}"""


def wcag_from_tags(tags: list[str] | None) -> str | None:
    for tag in tags or []:
        compact = re.match(r"^wcag(\d)(\d)(\d+)$", tag, re.I)
        if compact:
            return f"WCAG {compact.group(1)}.{compact.group(2)}.{int(compact.group(3))}"
    return None


def run_axe(page: Any, timeout_ms: int = AXE_TIMEOUT_MS) -> dict[str, Any]:
    if not AXE_BUNDLE.exists():
        raise ScanError("A11Y_FAILED", "Accessibility analysis could not be completed.")
    try:
        page.add_script_tag(path=str(AXE_BUNDLE))
        page.set_default_timeout(timeout_ms)
        return page.evaluate(AXE_RUN_JS, list(AXE_TAGS)) or {}
    except ScanError:
        raise
    except Exception as exc:
        logger.exception("axe_run_failed")
        raise ScanError("A11Y_FAILED", "Accessibility analysis could not be completed.") from exc


def _nodes_summary(nodes: list[dict]) -> tuple[str | None, int, str | None]:
    count = len(nodes or [])
    first = (nodes or [None])[0] or {}
    targets = first.get("target") or []
    selector = sanitize_selector(targets[0] if targets else None)
    detected = sanitize_text(first.get("failureSummary") or first.get("html"))
    return selector, count, detected


def _severity(impact: str | None) -> str:
    return IMPACT_SEVERITY.get((impact or "").lower(), "medium")


def _group_for_unmapped(tags: list[str]) -> CheckGroup:
    joined = " ".join(tags or [])
    if "cat.color" in joined or "wcag1.4.3" in joined or "contrast" in joined:
        return "contrast"
    if "cat.forms" in joined:
        return "forms"
    if "cat.keyboard" in joined:
        return "keyboard"
    if "cat.aria" in joined:
        return "aria"
    if "cat.text-alternatives" in joined:
        return "images"
    if "cat.structure" in joined:
        return "landmarks"
    return "other"


def axe_to_checks(axe: dict[str, Any], page_url: str) -> list[CheckResult]:
    grouped: dict[str, CheckResult] = {}
    extras: list[CheckResult] = []

    def absorb(item: dict, *, status: str, manual: bool) -> None:
        rule_id = str(item.get("id") or "unknown")
        mapped = AXE_CHECK_MAP.get(rule_id)
        selector, count, detected = _nodes_summary(item.get("nodes") or [])
        wcag = wcag_from_tags(item.get("tags") or [])
        message = sanitize_text(item.get("help") or item.get("description") or rule_id, 200) or rule_id
        if status == "warning":
            message = f"{message} Manual review may be required."
        if mapped:
            check_id, group, name = mapped
            existing = grouped.get(check_id)
            if existing and existing.status == "fail" and status == "warning":
                return
            grouped[check_id] = make_check(
                check_id=check_id,
                name=name,
                group=group,
                status=status,  # type: ignore[arg-type]
                severity=_severity(item.get("impact")),  # type: ignore[arg-type]
                message=message,
                page_url=page_url,
                recommendation=sanitize_text(item.get("description"), 240),
                why="This finding comes from axe-core automated rules on the rendered page.",
                detected=detected,
                selector=selector,
                affected_element_count=max(count, existing.affected_element_count if existing else 0),
                wcag_reference=wcag,
                source="axe",
                details={"axe_rule": rule_id, "impact": item.get("impact")},
                help_url=item.get("helpUrl"),
                axe_rule_id=rule_id,
                manual_review=manual,
            )
            return
        extras.append(
            make_check(
                check_id=f"A11Y-AXE-{rule_id}",
                name=sanitize_text(item.get("help"), 80) or rule_id,
                group=_group_for_unmapped(item.get("tags") or []),
                status=status,  # type: ignore[arg-type]
                severity=_severity(item.get("impact")),  # type: ignore[arg-type]
                message=message,
                page_url=page_url,
                recommendation=sanitize_text(item.get("description"), 240),
                why="This finding comes from axe-core automated rules on the rendered page.",
                detected=detected,
                selector=selector,
                affected_element_count=count,
                wcag_reference=wcag,
                source="axe",
                details={"axe_rule": rule_id, "impact": item.get("impact")},
                help_url=item.get("helpUrl"),
                axe_rule_id=rule_id,
                manual_review=manual,
            )
        )

    for item in axe.get("violations") or []:
        absorb(item, status="fail", manual=False)
    for item in axe.get("incomplete") or []:
        absorb(item, status="warning", manual=True)
    return list(grouped.values()) + extras
