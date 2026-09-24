"""Deterministic comparison aggregation from stored scan snapshots."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.competitors.config import (
    ANALYZER_CATEGORIES,
    ISSUE_LABELS,
    LIMITATIONS,
    MAX_ISSUE_ROWS,
    MAX_OBSERVATIONS,
    METHODOLOGY,
    METHODOLOGY_VERSION,
    STALE_SECONDS,
    methodology_snapshot,
    scope_note,
)
from backend.competitors.snapshot import snapshot_from_record
from backend.schemas.scan import ScanRecord


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _stale_label(primary_completed: str | None, other_completed: str | None) -> str | None:
    left = _parse_dt(primary_completed)
    right = _parse_dt(other_completed)
    if left is None or right is None:
        return None
    delta = (left - right).total_seconds()
    if abs(delta) < STALE_SECONDS:
        return None
    days = int(abs(delta) // 86400)
    if days < 1:
        return None
    if delta > 0:
        return f"Scanned {days} day{'s' if days != 1 else ''} earlier."
    return f"Scanned {days} day{'s' if days != 1 else ''} later than the primary scan."


def _cell(available: bool, value: Any = None, display: str | None = None) -> dict[str, Any]:
    if not available or value is None:
        return {"available": False, "value": None, "display": None}
    if display is None:
        if isinstance(value, float) and not value.is_integer():
            display = str(value)
        else:
            display = str(value)
    return {"available": True, "value": value, "display": display}


def _metric_row(metric_id: str, label: str, group: str, columns: list[dict[str, Any]], getter, *, direction: str = "neutral", unit: str | None = None) -> dict[str, Any]:
    values = []
    for column in columns:
        available, value, display = getter(column)
        values.append({**_cell(available, value, display), "column_id": column["column_id"]})
    primary = next((item for item in values if item["column_id"] == "primary"), None)
    differences = []
    if direction == "higher_score" and primary and primary.get("available"):
        for item in values:
            if item["column_id"] == "primary" or not item.get("available"):
                continue
            if isinstance(primary.get("value"), (int, float)) and isinstance(item.get("value"), (int, float)):
                diff = primary["value"] - item["value"]
                differences.append(
                    {
                        "column_id": item["column_id"],
                        "value": diff,
                        "display": f"+{diff}" if diff > 0 else str(diff),
                    }
                )
    return {
        "id": metric_id,
        "label": label,
        "group": group,
        "direction": direction,
        "unit": unit,
        "values": values,
        "differences": differences,
    }


def _issue_label(key: str, title: str) -> str:
    return ISSUE_LABELS.get(key) or title or key


def _observations(primary: dict[str, Any], competitors: list[dict[str, Any]]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    primary_issues = primary.get("issues") or {}
    primary_pages = primary.get("pages") or {}
    primary_perf = primary.get("performance") or {}
    for competitor in competitors:
        if competitor.get("status") != "completed":
            if competitor.get("status") == "failed":
                items.append(
                    {
                        "id": f"failed-{competitor['column_id']}",
                        "text": f"{competitor['label']} scan failed.",
                    }
                )
            elif competitor.get("status") in {"queued", "running", "scanning"}:
                items.append(
                    {
                        "id": f"pending-{competitor['column_id']}",
                        "text": "Comparison will update when the competitor scan completes.",
                    }
                )
            continue
        other_issues = competitor.get("issues") or {}
        if primary_issues.get("available") and other_issues.get("available"):
            p_total = primary_issues.get("total")
            c_total = other_issues.get("total")
            if p_total is not None and c_total is not None:
                items.append(
                    {
                        "id": f"issues-{competitor['column_id']}",
                        "text": f"{competitor['label']} recorded {c_total} open issue types compared with {p_total} on the primary site.",
                    }
                )
        other_pages = competitor.get("pages") or {}
        if primary_pages.get("available") and other_pages.get("available"):
            items.append(
                {
                    "id": f"pages-{competitor['column_id']}",
                    "text": f"{competitor['label']} has {other_pages.get('crawled')} crawled pages, while the primary scan contains {primary_pages.get('crawled')}.",
                }
            )
        other_perf = competitor.get("performance") or {}
        lcp = (other_perf.get("lcp") or {}).get("value") if other_perf.get("available") else None
        if lcp is not None:
            seconds = round(lcp / 1000, 1) if lcp >= 100 else lcp
            unit = "seconds" if lcp >= 100 else "ms"
            items.append(
                {
                    "id": f"lcp-{competitor['column_id']}",
                    "text": f"{competitor['label']} recorded a measured LCP of {seconds} {unit} in this scan.",
                }
            )
        if len(items) >= MAX_OBSERVATIONS:
            break
    return items[:MAX_OBSERVATIONS]


def build_comparison(
    primary: ScanRecord,
    competitors: list[tuple[Any, ScanRecord]],
) -> dict[str, Any]:
    primary_snap = snapshot_from_record(primary, column_id="primary", label="Your site", role="primary")
    competitor_snaps = []
    for benchmark, record in competitors:
        label = benchmark.name
        snap = snapshot_from_record(record, column_id=benchmark.id, label=label, role="competitor")
        snap["benchmark_id"] = benchmark.id
        snap["competitor_scan_id"] = record.id
        snap["stale"] = _stale_label(primary_snap.get("completed_at"), snap.get("completed_at"))
        competitor_snaps.append(snap)

    columns = [primary_snap, *competitor_snaps]
    warnings: list[str] = []
    versions = {str(col.get("methodology_version") or METHODOLOGY_VERSION) for col in columns if col.get("status") == "completed"}
    if len(versions) > 1:
        warnings.append("These scans used different SiteLens methodology versions. Compare values with that difference in mind.")
    page_limits = {col.get("pages", {}).get("max_pages") for col in columns if col.get("pages", {}).get("available")}
    depth_limits = {col.get("pages", {}).get("max_depth") for col in columns if col.get("pages", {}).get("available")}
    if len({item for item in page_limits if item is not None}) > 1 or len({item for item in depth_limits if item is not None}) > 1:
        warnings.append("Crawl limits differ between scans. Coverage metrics are not directly equivalent.")
    env_keys = []
    for col in columns:
        perf = col.get("performance") or {}
        env = perf.get("environment") if perf.get("available") else None
        if env:
            env_keys.append((env.get("browser"), env.get("network_profile"), env.get("cache_mode"), str(env.get("viewport"))))
    if len(set(env_keys)) > 1:
        warnings.append("Performance measurement environments differ. Timing values are not directly equivalent.")

    categories = []
    for key, label in ANALYZER_CATEGORIES:
        values = []
        for col in columns:
            cat = (col.get("categories") or {}).get(key) or {}
            values.append(
                {
                    "column_id": col["column_id"],
                    "available": bool(cat.get("available")),
                    "status": cat.get("status") or "missing",
                    "score": cat.get("score") if cat.get("available") else None,
                    "analyzed_pages": (col.get("pages") or {}).get("crawled") if cat.get("available") else None,
                    "available_checks": cat.get("available_checks") if cat.get("available") else None,
                    "issue_count": cat.get("issue_count") if cat.get("available") else None,
                }
            )
        categories.append({"id": key, "label": label, "kind": "score", "values": values})
    if any((col.get("categories") or {}).get("cro") for col in columns):
        values = []
        for col in columns:
            cat = (col.get("categories") or {}).get("cro") or {}
            values.append(
                {
                    "column_id": col["column_id"],
                    "available": bool(cat.get("available")),
                    "status": cat.get("status") or "missing",
                    "score": cat.get("score") if cat.get("available") else None,
                    "analyzed_pages": (col.get("pages") or {}).get("crawled") if cat.get("available") else None,
                    "available_checks": cat.get("available_checks") if cat.get("available") else None,
                    "issue_count": cat.get("issue_count") if cat.get("available") else None,
                }
            )
        categories.append({"id": "cro", "label": "CRO", "kind": "score", "values": values})
    if any((col.get("categories") or {}).get("trust") for col in columns):
        values = []
        for col in columns:
            cat = (col.get("categories") or {}).get("trust") or {}
            values.append(
                {
                    "column_id": col["column_id"],
                    "available": bool(cat.get("available")),
                    "status": cat.get("status") or "missing",
                    "score": cat.get("score") if cat.get("available") else None,
                    "analyzed_pages": (col.get("pages") or {}).get("crawled") if cat.get("available") else None,
                    "available_checks": cat.get("available_checks") if cat.get("available") else None,
                    "issue_count": cat.get("issue_count") if cat.get("available") else None,
                }
            )
        categories.append({"id": "trust", "label": "Trust", "kind": "score", "values": values})

    def getter_score(key: str):
        def inner(col: dict[str, Any]):
            cat = (col.get("categories") or {}).get(key) or {}
            return bool(cat.get("available")), cat.get("score"), str(cat["score"]) if cat.get("available") and cat.get("score") is not None else None
        return inner

    metrics = [
        _metric_row("pages_crawled", "Pages crawled", "coverage", columns, lambda col: (bool((col.get("pages") or {}).get("available")), (col.get("pages") or {}).get("crawled"), None)),
        _metric_row("pages_discovered", "Pages discovered", "coverage", columns, lambda col: (bool((col.get("pages") or {}).get("available")), (col.get("pages") or {}).get("discovered"), None)),
        _metric_row("pages_failed", "Pages failed", "coverage", columns, lambda col: (bool((col.get("pages") or {}).get("available")), (col.get("pages") or {}).get("failed"), None)),
        _metric_row("pages_skipped", "Pages skipped", "coverage", columns, lambda col: (bool((col.get("pages") or {}).get("available")), (col.get("pages") or {}).get("skipped"), None)),
        _metric_row("max_depth_reached", "Maximum crawl depth reached", "coverage", columns, lambda col: (bool((col.get("pages") or {}).get("available")), (col.get("pages") or {}).get("max_depth_reached"), None)),
        _metric_row("issues_total", "Issue types", "issues", columns, lambda col: (bool((col.get("issues") or {}).get("available")), (col.get("issues") or {}).get("total"), None), direction="lower_quantity"),
        _metric_row("issue_occurrences", "Issue occurrences", "issues", columns, lambda col: (bool((col.get("issues") or {}).get("available")), (col.get("issues") or {}).get("occurrences"), None), direction="lower_quantity"),
        _metric_row("recommendations_total", "Recommendations", "recommendations", columns, lambda col: (bool((col.get("issues") or {}).get("recommendations_available")), (col.get("issues") or {}).get("recommendations_total"), None)),
        _metric_row("arch_pages", "Architecture pages", "architecture", columns, lambda col: (bool((col.get("architecture") or {}).get("available")), (col.get("architecture") or {}).get("page_count"), None)),
        _metric_row("internal_links", "Internal links", "architecture", columns, lambda col: (bool((col.get("architecture") or {}).get("available") and (col.get("architecture") or {}).get("links_recorded")), (col.get("architecture") or {}).get("internal_link_count"), None)),
        _metric_row("orphans", "Potential orphan pages", "architecture", columns, lambda col: (bool((col.get("architecture") or {}).get("available") and (col.get("architecture") or {}).get("links_recorded")), (col.get("architecture") or {}).get("potential_orphan_count"), None)),
        _metric_row("dead_ends", "Dead-end pages", "architecture", columns, lambda col: (bool((col.get("architecture") or {}).get("available") and (col.get("architecture") or {}).get("links_recorded")), (col.get("architecture") or {}).get("dead_end_count"), None)),
        _metric_row("avg_depth", "Average crawl depth", "architecture", columns, lambda col: (bool((col.get("architecture") or {}).get("available")), (col.get("architecture") or {}).get("average_crawl_depth"), None)),
        _metric_row("avg_words", "Average word count", "content", columns, lambda col: (bool((col.get("pages") or {}).get("available")), (col.get("pages") or {}).get("average_word_count"), None), direction="higher_score"),
        _metric_row("ttfb_ms", "TTFB", "performance", columns, lambda col: (bool((col.get("performance") or {}).get("available") and (col.get("performance") or {}).get("ttfb_ms") is not None), (col.get("performance") or {}).get("ttfb_ms"), None), direction="lower_quantity", unit="ms"),
        _metric_row(
            "lcp_ms",
            "LCP",
            "performance",
            columns,
            lambda col: (
                bool(((col.get("performance") or {}).get("lcp") or {}).get("available")),
                ((col.get("performance") or {}).get("lcp") or {}).get("value"),
                None,
            ),
            direction="lower_quantity",
            unit="ms",
        ),
        _metric_row(
            "cls",
            "CLS",
            "performance",
            columns,
            lambda col: (
                bool(((col.get("performance") or {}).get("cls") or {}).get("available")),
                ((col.get("performance") or {}).get("cls") or {}).get("value"),
                None,
            ),
            direction="lower_quantity",
        ),
        _metric_row("resource_bytes", "Resource bytes", "performance", columns, lambda col: (bool((col.get("performance") or {}).get("available") and (col.get("performance") or {}).get("resource_bytes") is not None), (col.get("performance") or {}).get("resource_bytes"), None), direction="lower_quantity", unit="bytes"),
    ]
    for key, label in ANALYZER_CATEGORIES:
        metrics.append(_metric_row(f"score_{key}", f"{label} score", "scores", columns, getter_score(key), direction="higher_score"))
    if any((col.get("categories") or {}).get("cro") for col in columns):
        metrics.append(_metric_row("score_cro", "CRO score", "scores", columns, getter_score("cro"), direction="higher_score"))
    if any((col.get("categories") or {}).get("trust") for col in columns):
        metrics.append(_metric_row("score_trust", "Trust Signals score", "scores", columns, getter_score("trust"), direction="higher_score"))

    issue_keys: dict[str, dict[str, Any]] = {}
    for col in columns:
        issues = col.get("issues") or {}
        if not issues.get("available"):
            continue
        for key, row in (issues.get("by_key") or {}).items():
            meta = issue_keys.setdefault(key, {"issue_key": key, "title": _issue_label(key, row.get("title") or key), "category": row.get("category") or "", "counts": {}})
            meta["counts"][col["column_id"]] = row.get("count")
            if row.get("title") and meta["title"] == key:
                meta["title"] = _issue_label(key, row["title"])
    issue_rows = []
    column_ids = [col["column_id"] for col in columns]
    def _rank(item: tuple[str, dict[str, Any]]) -> tuple:
        counts = item[1]["counts"]
        values = [counts.get(column_id, 0) for column_id in column_ids]
        present = sum(1 for value in values if value)
        presence_spread = 1 if 0 < present < len(column_ids) else 0
        spread = (max(values) - min(values)) if values else 0
        return (-presence_spread, -spread, -sum(values), item[0])

    ranked = sorted(issue_keys.items(), key=_rank)
    labeled = [key for key in ISSUE_LABELS if key in issue_keys]
    rest = [key for key, _meta in ranked if key not in ISSUE_LABELS]
    issue_rows = []
    for key in labeled + rest:
        meta = issue_keys[key]
        values = []
        for col in columns:
            issues = col.get("issues") or {}
            if not issues.get("available"):
                values.append({"column_id": col["column_id"], "available": False, "value": None, "display": None})
            else:
                count = meta["counts"].get(col["column_id"], 0)
                values.append({"column_id": col["column_id"], "available": True, "value": count, "display": str(count)})
        issue_rows.append({"issue_key": meta["issue_key"], "label": meta["title"], "category": meta["category"], "values": values})
        if len(issue_rows) >= MAX_ISSUE_ROWS:
            break

    severity_rows = []
    for sev in ("critical", "high", "medium", "low", "info"):
        values = []
        for col in columns:
            issues = col.get("issues") or {}
            if not issues.get("available"):
                values.append({"column_id": col["column_id"], "available": False, "value": None})
            else:
                by_sev = issues.get("by_severity") or {}
                count = issues.get(sev)
                if count is None:
                    count = by_sev.get(sev, 0)
                values.append({"column_id": col["column_id"], "available": True, "value": count, "display": str(count)})
        severity_rows.append({"id": sev, "label": sev.replace("_", " ").title(), "values": values})

    current = methodology_snapshot()
    max_pages = next((col.get("pages", {}).get("max_pages") for col in columns if col.get("pages", {}).get("max_pages")), current["max_pages"])
    max_depth = next((col.get("pages", {}).get("max_depth") for col in columns if col.get("pages", {}).get("max_depth")), current["max_depth"])

    return {
        "primary": {
            "column_id": "primary",
            "label": primary_snap["label"],
            "scan_id": primary.id,
            "url": primary_snap["normalized_url"],
            "status": primary.status,
            "completed_at": primary_snap.get("completed_at"),
            "created_at": primary_snap.get("created_at"),
        },
        "competitors": [
            {
                "column_id": snap["column_id"],
                "label": snap["label"],
                "scan_id": snap["scan_id"],
                "competitor_scan_id": snap["competitor_scan_id"],
                "url": snap["normalized_url"],
                "status": "scanning" if snap["status"] == "running" else snap["status"],
                "progress": snap.get("progress"),
                "current_step": snap.get("current_step"),
                "completed_at": snap.get("completed_at"),
                "created_at": snap.get("created_at"),
                "stale": snap.get("stale"),
                "error": snap.get("error"),
            }
            for snap in competitor_snaps
        ],
        "columns": [
            {
                "id": col["column_id"],
                "label": col["label"],
                "role": col["role"],
                "scan_id": col["scan_id"],
                "url": col["normalized_url"],
                "status": "scanning" if col["status"] == "running" else col["status"],
                "completed_at": col.get("completed_at"),
                "created_at": col.get("created_at"),
            }
            for col in columns
        ],
        "categories": categories,
        "metrics": metrics,
        "issues": issue_rows,
        "severity": severity_rows,
        "observations": _observations(primary_snap, competitor_snaps),
        "warnings": warnings,
        "methodology": {
            "version": current["version"],
            "text": METHODOLOGY,
            "limitations": LIMITATIONS,
            "scope": scope_note(max_pages, max_depth),
            "max_pages": max_pages,
            "max_depth": max_depth,
            "viewports": current["viewports"],
        },
        "incomplete": any(snap.get("status") not in {"completed", "failed", "cancelled"} for snap in competitor_snaps),
    }
