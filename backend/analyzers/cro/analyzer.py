"""CRO analyzer. Consumes stored crawl, UI/UX, mobile, accessibility, and architecture data."""

from __future__ import annotations

import logging
from collections import deque
from typing import Any
from urllib.parse import urlsplit

from backend.analyzers.cro.checks import CHECK_RUNNERS
from backend.analyzers.cro.config import (
    CRAWL_NOTE,
    DESKTOP_VIEWPORT,
    LIMITATIONS,
    METHODOLOGY,
    MOBILE_VIEWPORT,
    SCORE_NOTE,
    TABLET_VIEWPORT,
    CONVERSION_PAGE_TYPES,
)
from backend.analyzers.cro.context import PageCroContext
from backend.analyzers.cro.extraction import cro_page_type, merge_viewport_ctas
from backend.analyzers.cro.models import CroCtaRow, CroFormRow, CroPageInfo, CroPath, CroPathNode, CroResult
from backend.analyzers.cro.scoring import (
    apply_weights,
    category_cards,
    category_scores,
    collect_issues,
    narrative_summary,
    overall_score,
    summarize,
)
from backend.analyzers.cro.checks._util import actionable_status, primary_ctas
from backend.architecture.engine import build_architecture
from backend.errors import ScanError
from backend.pages.engine import payload_from_result
from backend.pages.models import PageRecord, PagesPayload

logger = logging.getLogger("sitebench.cro")


def _nav_count(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, list):
        return len(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _viewport_map(uiux: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(uiux, dict):
        return {}
    viewports = uiux.get("viewports") or {}
    return viewports if isinstance(viewports, dict) else {}


def _a11y_form_labels(result: dict[str, Any]) -> bool:
    payload = result.get("accessibility")
    if not isinstance(payload, dict):
        return False
    for check in payload.get("checks") or payload.get("findings") or []:
        if not isinstance(check, dict):
            continue
        check_id = str(check.get("check_id") or "")
        if check_id in {"A11Y-FORM-001"} and check.get("status") in {"fail", "warning"}:
            return True
    return False


def _site_contact(pages: list[PageRecord]) -> bool:
    for page in pages:
        if (page.page_type or "") == "contact":
            return True
        signals = page.cro_signals or {}
        contact = signals.get("contact") or {}
        if contact.get("emails") or contact.get("phones") or contact.get("links") or contact.get("form"):
            return True
        path = (urlsplit(page.normalized_url or page.url).path or "").lower()
        if "/contact" in path:
            return True
    return False


def _conversion_pages(pages: list[PageRecord]) -> bool:
    for page in pages:
        kind = cro_page_type(page.page_type, page.normalized_url or page.url)
        if kind in CONVERSION_PAGE_TYPES:
            return True
    return False


def _bfs_path(pages: list[PageRecord], start: PageRecord, graph) -> list[dict[str, Any]]:
    if start.id not in graph.nodes:
        return []
    goals = {
        node.page.id
        for node in graph.nodes.values()
        if cro_page_type(node.page.page_type, node.page.normalized_url or node.page.url) in CONVERSION_PAGE_TYPES
        and node.page.id != start.id
    }
    if not goals or not (graph.links_recorded or graph.links):
        return []
    queue: deque[list[str]] = deque([[start.id]])
    seen = {start.id}
    while queue:
        path = queue.popleft()
        last = path[-1]
        if last in goals and last != start.id:
            nodes = []
            for page_id in path:
                stats = graph.nodes.get(page_id)
                if stats is None:
                    continue
                nodes.append(
                    {
                        "page_id": stats.page.id,
                        "url": stats.page.normalized_url or stats.page.url,
                        "title": stats.page.title,
                        "page_type": cro_page_type(stats.page.page_type, stats.page.normalized_url or stats.page.url),
                    }
                )
            return nodes
        for link in graph.nodes[last].outbound:
            dest = link.destination_page_id
            if dest in seen or dest not in graph.nodes:
                continue
            seen.add(dest)
            queue.append(path + [dest])
    return []


def _cta_rows(ctx: PageCroContext) -> list[CroCtaRow]:
    rows: list[CroCtaRow] = []
    primaries = {id(item) for item in primary_ctas(ctx)[:1]}
    for item in ctx.ctas:
        visibility = "Unavailable"
        if item.get("in_viewport") is True:
            visibility = "Visible"
        elif item.get("clipped"):
            visibility = "Clipped"
        elif item.get("visible") is False:
            visibility = "Hidden"
        elif ctx.rendered and item.get("in_viewport") is False:
            visibility = "Offscreen"
        status = "Pass"
        if item.get("broken") or item.get("disabled"):
            status = "Warning"
        elif item.get("vague"):
            status = "Warning"
        rows.append(
            CroCtaRow(
                text=str(item.get("text") or ""),
                page_url=ctx.url,
                page_id=ctx.page.id,
                kind=str(item.get("kind") or "link").title(),
                visibility=visibility,
                destination=str(item.get("destination") or "unknown"),
                status=status,
                primary=id(item) in primaries,
                selector=item.get("selector"),
            )
        )
    return rows


def _form_rows(ctx: PageCroContext, checks) -> list[CroFormRow]:
    rows: list[CroFormRow] = []
    form_issues = [item for item in checks if item.group == "forms" and item.status in {"fail", "warning"}]
    for form in ctx.forms:
        mobile_status = None
        if ctx.mobile_rendered:
            mobile_status = "Warning" if ctx.mobile_forms_overflow else "Pass"
        rows.append(
            CroFormRow(
                page_url=ctx.url,
                page_id=ctx.page.id,
                purpose=str(form.get("purpose") or "Unknown").title() if form.get("purpose") != "unknown" else "Unknown",
                fields=int(form.get("fields") or 0),
                submit_text=form.get("submit_text"),
                mobile_status=mobile_status,
                issue_count=len(form_issues),
                selector=form.get("selector"),
            )
        )
    return rows


def collect_checks(ctx: PageCroContext):
    checks = []
    for runner in CHECK_RUNNERS:
        checks.extend(runner(ctx))
    return checks


def analyze_cro(result: dict[str, Any] | None, *, pages: PagesPayload | None = None) -> CroResult:
    payload = result or {}
    pages_payload = pages if pages is not None else payload_from_result(payload)
    crawled = [page for page in pages_payload.items if page.crawl_status == "crawled"]
    if not crawled:
        seed = next((page for page in pages_payload.items if page.is_seed), None)
        if seed is None:
            raise ScanError("CRO_FAILED", "CRO analysis could not be completed.")
        crawled = [seed]

    uiux = payload.get("uiux") if isinstance(payload.get("uiux"), dict) else None
    mobile = payload.get("mobile") if isinstance(payload.get("mobile"), dict) else None
    viewports = _viewport_map(uiux)
    desktop = viewports.get("desktop")
    graph = build_architecture(pages_payload if pages_payload.items else payload)
    a11y_labels = _a11y_form_labels(payload)
    site_contact = _site_contact(crawled)
    site_conversion = _conversion_pages(crawled)

    all_checks = []
    page_infos: list[CroPageInfo] = []
    cta_rows: list[CroCtaRow] = []
    form_rows: list[CroFormRow] = []
    paths: list[CroPath] = []

    html_block = payload.get("html") or {}

    for page in crawled:
        url = page.normalized_url or page.url
        signals = dict(page.cro_signals or {})
        if not signals.get("ctas") and not signals.get("forms") and page.is_seed:
            # Homepage HTML is not persisted raw; UI/UX measurements plus page metadata still apply.
            signals.setdefault("h1", page.h1 or html_block.get("h1"))
            signals.setdefault("h1_present", bool(page.h1 or html_block.get("h1")))
            signals.setdefault("supporting_text", None)
            signals.setdefault("generic_h1", False)
            signals.setdefault("ctas", [])
            signals.setdefault("forms", [])
            signals.setdefault("contact", {"emails": [], "phones": [], "links": [], "form": False})
            signals.setdefault("pricing", {"price_text": False, "plan_text": False, "quote_cta": False})
            signals.setdefault("trust", [])
        rendered = bool(page.is_seed and desktop)
        mobile_rendered = bool(page.is_seed and mobile)
        ctas = list(signals.get("ctas") or [])
        forms = list(signals.get("forms") or [])
        if rendered and desktop:
            ctas = merge_viewport_ctas({**signals, "page_url": url}, desktop, viewport_name="desktop")
            if not forms:
                for form in desktop.get("forms") or []:
                    forms.append(
                        {
                            "selector": form.get("selector"),
                            "fields": int(form.get("fields") or 0),
                            "field_details": [],
                            "submit_text": None,
                            "purpose": "unknown",
                            "placeholder_only": 0,
                            "unlabeled": max(0, int(form.get("fields") or 0) - int(form.get("labeled") or 0)),
                            "required": 0,
                            "has_email": False,
                            "has_phone": False,
                            "has_password": False,
                        }
                    )
        if not signals.get("supporting_text") and page.meta_description:
            signals["supporting_text"] = page.meta_description
        ctx = PageCroContext(
            page=page,
            url=url,
            page_type=cro_page_type(page.page_type, url),
            signals=signals,
            ctas=ctas,
            forms=forms,
            desktop=desktop if page.is_seed else None,
            mobile=mobile if page.is_seed else None,
            a11y_form_label_issue=a11y_labels,
            site_has_contact=site_contact,
            site_has_conversion_page=site_conversion,
            conversion_path=_bfs_path(crawled, page, graph) if page.is_seed else [],
            rendered=rendered,
            mobile_rendered=mobile_rendered,
            nav_links=_nav_count((desktop.get("navigation") or {}).get("links") if desktop and page.is_seed else None),
            overlays=list((desktop.get("overlays") or []) if desktop and page.is_seed else []),
            mobile_forms_overflow=bool((mobile or {}).get("forms", {}).get("overflowing_forms")) if page.is_seed else False,
            mobile_cta=dict((mobile or {}).get("cta") or {}) if page.is_seed else {},
        )
        page_checks = apply_weights(collect_checks(ctx))
        all_checks.extend(page_checks)
        cta_rows.extend(_cta_rows(ctx))
        form_rows.extend(_form_rows(ctx, page_checks))
        score = overall_score(page_checks)
        page_infos.append(
            CroPageInfo(
                page_id=page.id,
                url=url,
                page_type=ctx.page_type,
                score=score,
                available=True,
                cta_status=actionable_status(page_checks, "primary_cta"),
                forms_status=actionable_status(page_checks, "forms"),
                conversion_path_status=actionable_status(page_checks, "conversion_path"),
                issue_count=sum(1 for item in page_checks if item.status in {"fail", "warning"}),
            )
        )
        if ctx.conversion_path:
            paths.append(
                CroPath(
                    nodes=[
                        CroPathNode(url=node["url"], title=node.get("title"), page_type=node.get("page_type"))
                        for node in ctx.conversion_path
                    ]
                )
            )
        trust = signals.get("trust") or []
        if trust and primary_ctas(ctx):
            for check in page_checks:
                if check.check_id == "cro.cta.primary.missing" and check.status == "pass":
                    check.evidence["trust_near_cta"] = "Trust signal detected near primary CTA."

    if not paths:
        paths.append(CroPath(nodes=[], message="No conversion path could be determined from the crawled links."))

    score = overall_score(all_checks)
    summary = summarize(all_checks, pages_analyzed=len(page_infos))
    shots = []
    if uiux:
        for item in uiux.get("screenshots") or []:
            if isinstance(item, dict) and item.get("viewport") in {"desktop", "mobile"}:
                shots.append(item)
    return CroResult(
        score=score,
        summary=summary,
        narrative=narrative_summary(score, summary),
        categories=category_scores(all_checks),
        category_cards=category_cards(all_checks),
        checks=all_checks,
        findings=all_checks,
        issues=collect_issues(all_checks),
        pages=page_infos,
        ctas=cta_rows,
        forms=form_rows,
        conversion_paths=paths,
        methodology=METHODOLOGY,
        limitations=list(LIMITATIONS),
        screenshots=shots,
        score_note=SCORE_NOTE,
        crawl_note=CRAWL_NOTE,
        viewports={
            "desktop": {"width": DESKTOP_VIEWPORT[0], "height": DESKTOP_VIEWPORT[1]},
            "tablet": {"width": TABLET_VIEWPORT[0], "height": TABLET_VIEWPORT[1]},
            "mobile": {"width": MOBILE_VIEWPORT[0], "height": MOBILE_VIEWPORT[1]},
        },
    )
