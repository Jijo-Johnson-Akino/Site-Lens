"""Trust & Credibility analyzer. Reuses crawl, AEO, content, structured data, and CRO contact signals."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

from backend.analyzers.trust.checks import PAGE_RUNNERS, SITE_RUNNERS
from backend.analyzers.trust.checks._util import first_name
from backend.analyzers.trust.config import (
    ABOUT_PAGE_TYPES,
    ARTICLE_PAGE_TYPES,
    COMMERCE_PAGE_TYPES,
    CRAWL_NOTE,
    LIMITATIONS,
    LOGIN_PAGE_TYPES,
    METHODOLOGY,
    ORG_SCHEMA_TYPES,
    POLICY_LABELS,
    SCORE_NOTE,
)
from backend.analyzers.trust.context import PageTrustContext, SiteTrustContext
from backend.analyzers.trust.extraction import (
    extract_signals,
    merge_content_signals,
    merge_cro_contact,
    merge_schema_entities,
    trust_page_type,
)
from backend.analyzers.trust.models import (
    TrustAuthorRow,
    TrustConsistencyRow,
    TrustPageInfo,
    TrustPolicyRow,
    TrustResult,
    TrustSecurityRow,
    TrustSignalRow,
    TrustSocialProofRow,
)
from backend.analyzers.trust.scoring import (
    apply_weights,
    category_cards,
    category_scores,
    collect_issues,
    narrative_summary,
    overall_score,
    summarize,
)
from backend.errors import ScanError
from backend.pages.engine import payload_from_result
from backend.pages.models import PageRecord, PagesPayload
from backend.services.url_identity import hostname_of

logger = logging.getLogger("sitebench.trust")


def actionable_status_safe(checks, group: str) -> str | None:
    subset = [item for item in checks if item.group == group]
    if not subset:
        return None
    if any(item.status == "fail" for item in subset):
        return "fail"
    if any(item.status == "warning" for item in subset):
        return "warning"
    if any(item.status == "pass" for item in subset):
        return "pass"
    return "not_applicable"


def _https(url: str | None) -> bool:
    return (urlsplit(url or "").scheme or "").lower() == "https"


def _schema_entities(result: dict[str, Any]) -> list[dict[str, Any]]:
    payload = result.get("structured_data")
    if not isinstance(payload, dict):
        return []
    entities = []
    for item in payload.get("entities") or []:
        if not isinstance(item, dict):
            continue
        entities.append(
            {
                "types": list(item.get("types") or []),
                "name": item.get("name"),
                "properties": item.get("properties") if isinstance(item.get("properties"), dict) else {},
            }
        )
    return entities


def _html_entities(html: dict[str, Any] | None) -> list[dict[str, Any]]:
    block = (html or {}).get("json_ld") if isinstance(html, dict) else None
    if not isinstance(block, dict):
        return []
    return [item for item in (block.get("entities") or []) if isinstance(item, dict)]


def _seed_signals(page: PageRecord, result: dict[str, Any]) -> dict[str, Any]:
    signals = dict(page.trust_signals or {})
    html = result.get("html") if isinstance(result.get("html"), dict) else {}
    if not signals:
        parsed = html
        synthetic = {
            "json_ld": parsed.get("json_ld") or {},
            "emails": parsed.get("emails") or [],
            "tel_links": parsed.get("tel_links") or [],
            "mailto_links": parsed.get("mailto_links") or [],
            "links": parsed.get("links") or [],
            "visible_text": parsed.get("visible_text") or "",
            "h1s": parsed.get("h1s") or ([{"text": parsed.get("h1")}] if parsed.get("h1") else []),
            "header_identity": parsed.get("header_identity"),
            "og_site_name": parsed.get("og_site_name"),
            "title": parsed.get("title") or page.title,
            "byline": parsed.get("byline"),
            "author_rel": parsed.get("author_rel"),
            "time_values": parsed.get("time_values") or [],
            "has_address": parsed.get("has_address"),
            "form_count": parsed.get("form_count") or 0,
            "headings": parsed.get("headings") or page.headings,
        }
        try:
            signals = extract_signals("", page.normalized_url or page.url, parsed=synthetic)
        except Exception:
            logger.info("trust_seed_extract_failed url=%s", page.normalized_url)
            signals = {}
    signals = merge_schema_entities(signals, _schema_entities(result) if page.is_seed else [])
    if page.is_seed:
        signals = merge_schema_entities(signals, _html_entities(html))
        signals = merge_content_signals(signals, result.get("content") if isinstance(result.get("content"), dict) else None)
    signals = merge_cro_contact(signals, page.cro_signals)
    return signals


def _aeo_names(result: dict[str, Any]) -> dict[str, str]:
    names: dict[str, str] = {}
    html = result.get("html") if isinstance(result.get("html"), dict) else {}
    if html.get("og_site_name"):
        names["og"] = str(html["og_site_name"])
    if html.get("header_identity"):
        names["header"] = str(html["header_identity"])
    aeo = result.get("aeo") if isinstance(result.get("aeo"), dict) else {}
    for check in aeo.get("checks") or aeo.get("findings") or []:
        if not isinstance(check, dict):
            continue
        check_id = str(check.get("check_id") or "")
        detected = check.get("detected")
        if detected and (check_id.startswith("AEO-ENTITY") or check_id.startswith("AEO-ORG")):
            names.setdefault("aeo", str(detected).split(",")[0].strip())
    return names


def build_contexts(
    crawled: list[PageRecord],
    result: dict[str, Any],
    *,
    current_year: int,
) -> SiteTrustContext:
    website = result.get("website") if isinstance(result.get("website"), dict) else {}
    seed = next((page for page in crawled if page.is_seed), crawled[0])
    seed_url = website.get("final_url") or website.get("url") or seed.normalized_url or seed.url
    host = hostname_of(seed_url) or ""
    https = _https(seed_url)
    schema_entities = _schema_entities(result)
    page_ctxs: list[PageTrustContext] = []
    for page in crawled:
        url = page.normalized_url or page.url
        signals = _seed_signals(page, result) if page.is_seed else dict(page.trust_signals or {})
        if not page.is_seed:
            signals = merge_cro_contact(signals, page.cro_signals)
        kind = trust_page_type(page.page_type, url)
        page_ctxs.append(
            PageTrustContext(
                page=page,
                url=url,
                page_type=kind,
                signals=signals,
                schema_entities=schema_entities if page.is_seed else [],
                https=_https(url),
                site_host=host,
                current_year=current_year,
                is_seed=page.is_seed,
            )
        )

    org_names: dict[str, str] = {}
    org_names.update(_aeo_names(result))
    emails: list[str] = []
    email_pages: dict[str, str] = {}
    phones: list[str] = []
    addresses: list[str] = []
    about_pages: list[dict[str, Any]] = []
    about_links: list[dict[str, Any]] = []
    contact_pages: list[dict[str, Any]] = []
    policies: dict[str, list[dict[str, Any]]] = {key: [] for key in POLICY_LABELS}
    social_profiles: list[dict[str, str]] = []
    schema_types: set[str] = set()
    hours: list[str] = []
    identifiers: list[str] = []
    copyright_years: list[int] = []
    logo = False
    has_product = False
    has_articles = False
    has_login = False
    citations = False
    methodology = False
    footer_present = False
    article_count = 0
    articles_with_author = 0
    articles_with_date = 0
    latest_date = None
    contact_forms = False

    for ctx in page_ctxs:
        identity = ctx.signals.get("identity") or {}
        if identity.get("visible_name") and "visible" not in org_names:
            org_names["visible"] = identity["visible_name"]
        if identity.get("header_name"):
            org_names.setdefault("header", identity["header_name"])
        if identity.get("footer_name"):
            org_names.setdefault("footer", identity["footer_name"])
        if identity.get("og_site_name"):
            org_names.setdefault("og", identity["og_site_name"])
        if identity.get("h1") and ctx.page_type == "about":
            org_names.setdefault("about", identity["h1"])
        for item in identity.get("schema_names") or []:
            types = set(item.get("types") or [])
            schema_types.update(str(t) for t in types)
            name = item.get("name")
            if name and types & ORG_SCHEMA_TYPES:
                org_names.setdefault("schema", str(name))
            elif name:
                org_names.setdefault("schema_other", str(name))
        schema_types.update(str(item) for item in (identity.get("schema_types") or []))
        schema_types.update(str(item) for item in (ctx.page.schema_types or []))
        if identity.get("logo"):
            logo = True
        contact = ctx.signals.get("contact") or {}
        for email in contact.get("emails") or []:
            if email not in emails:
                emails.append(email)
                email_pages[email] = ctx.url
        for phone in contact.get("phones") or []:
            if phone not in phones:
                phones.append(phone)
        address = contact.get("address_text") or (ctx.signals.get("business") or {}).get("address")
        if address and address not in addresses:
            addresses.append(address)
        if contact.get("form"):
            contact_forms = True
        if ctx.page_type in ABOUT_PAGE_TYPES or ctx.page.page_type == "about":
            about_pages.append({"url": ctx.url, "page_id": ctx.page.id, "title": ctx.page.title})
        about_links.extend((ctx.signals.get("about") or {}).get("links") or [])
        if ctx.page_type in {"contact"} or ctx.page.page_type == "contact":
            contact_pages.append({"url": ctx.url, "page_id": ctx.page.id, "title": ctx.page.title})
        for key, items in ((ctx.signals.get("policies") or {})).items():
            if key in policies:
                policies[key].extend(items or [])
        for profile in (ctx.signals.get("social") or {}).get("profiles") or []:
            if profile not in social_profiles:
                social_profiles.append(profile)
        hours.extend((ctx.signals.get("business") or {}).get("hours") or [])
        identifiers.extend((ctx.signals.get("business") or {}).get("identifiers") or [])
        copyright_years.extend((ctx.signals.get("footer") or {}).get("copyright_years") or [])
        if ctx.page_type in COMMERCE_PAGE_TYPES or ctx.page_type == "pricing":
            has_product = True
        if ctx.page_type in LOGIN_PAGE_TYPES:
            has_login = True
        transparency = ctx.signals.get("transparency") or {}
        if transparency.get("citations"):
            citations = True
        if transparency.get("methodology"):
            methodology = True
        footer = ctx.signals.get("footer") or {}
        if footer.get("company_name") or footer.get("copyright_years") or footer.get("has_privacy") or footer.get("has_terms"):
            footer_present = True
        if ctx.page_type in ARTICLE_PAGE_TYPES:
            has_articles = True
            article_count += 1
            authors = (ctx.signals.get("authorship") or {}).get("authors") or []
            dates = (ctx.signals.get("authorship") or {}).get("dates") or []
            if authors:
                articles_with_author += 1
            if dates:
                articles_with_date += 1
                if latest_date is None:
                    latest_date = dates[0]
        if (ctx.signals.get("business") or {}).get("schema_address") and not addresses:
            addresses.append("Address present in structured data")

    for entity in schema_entities:
        types = set(entity.get("types") or [])
        schema_types.update(str(item) for item in types)
        if entity.get("name") and types & ORG_SCHEMA_TYPES:
            org_names.setdefault("schema", str(entity["name"]))
        props = entity.get("properties") or {}
        if props.get("email") and props["email"] not in emails:
            emails.append(str(props["email"]))
        if props.get("telephone") and props["telephone"] not in phones:
            phones.append(str(props["telephone"]))
        if props.get("address") and not addresses:
            addresses.append(str(props["address"])[:160])
        if props.get("openingHours"):
            hours.append(str(props["openingHours"]))

    return SiteTrustContext(
        seed_url=seed_url,
        seed_page_id=seed.id,
        host=host,
        https=https,
        current_year=current_year,
        pages=page_ctxs,
        org_names=org_names,
        emails=emails,
        email_pages=email_pages,
        phones=phones,
        addresses=addresses,
        about_pages=about_pages,
        about_links=about_links[:12],
        contact_pages=contact_pages,
        contact_forms=contact_forms,
        policies=policies,
        social_profiles=social_profiles[:12],
        schema_types=schema_types,
        schema_entities=schema_entities,
        logo=logo,
        hours=list(dict.fromkeys(hours))[:6],
        identifiers=list(dict.fromkeys(identifiers))[:6],
        copyright_years=list(dict.fromkeys(copyright_years))[:6],
        has_product=has_product,
        has_articles=has_articles,
        has_login=has_login,
        citations=citations,
        methodology=methodology,
        footer_present=footer_present,
        article_count=article_count,
        articles_with_author=articles_with_author,
        articles_with_date=articles_with_date,
        latest_date=latest_date,
    )


def _collect(site: SiteTrustContext):
    checks = []
    for runner in SITE_RUNNERS:
        checks.extend(runner(site))
    for ctx in site.pages:
        for runner in PAGE_RUNNERS:
            checks.extend(runner(ctx))
    return apply_weights(checks)


def _signal_rows(checks) -> tuple[list[TrustSignalRow], list[TrustSignalRow]]:
    signals: list[TrustSignalRow] = []
    gaps: list[TrustSignalRow] = []
    for check in checks:
        row = TrustSignalRow(
            signal=check.message,
            category=check.group,
            page_url=check.page_url,
            page_id=check.page_id,
            evidence=str(check.detected or check.evidence or "")[:180],
            status=check.status,
        )
        if check.status == "pass":
            signals.append(row)
        elif check.status in {"fail", "warning"}:
            gaps.append(row)
    return signals[:80], gaps[:80]


def _policy_rows(site: SiteTrustContext) -> list[TrustPolicyRow]:
    rows = []
    for key, label in POLICY_LABELS.items():
        items = site.policies.get(key) or []
        if items:
            rows.append(
                TrustPolicyRow(
                    policy=label,
                    detected=True,
                    page_url=items[0].get("href"),
                    note="Detected",
                )
            )
        else:
            rows.append(
                TrustPolicyRow(
                    policy=label,
                    detected=False,
                    page_url=None,
                    note="Not detected within crawl",
                )
            )
    return rows


def _author_rows(site: SiteTrustContext) -> list[TrustAuthorRow]:
    rows: list[TrustAuthorRow] = []
    for ctx in site.pages:
        if ctx.page_type not in ARTICLE_PAGE_TYPES:
            continue
        authorship = ctx.signals.get("authorship") or {}
        authors = authorship.get("authors") or []
        schema_authors = authorship.get("schema_authors") or []
        dates = authorship.get("dates") or []
        rows.append(
            TrustAuthorRow(
                page_url=ctx.url,
                page_id=ctx.page.id,
                title=ctx.page.title or ctx.page.h1,
                author=authors[0] if authors else None,
                publication_date=authorship.get("published") or (dates[0] if dates else None),
                modified_date=authorship.get("modified"),
                author_schema=schema_authors[0] if schema_authors else None,
                available=True,
            )
        )
    return rows[:40]


def _social_rows(site: SiteTrustContext) -> list[TrustSocialProofRow]:
    rows: list[TrustSocialProofRow] = []
    for ctx in site.pages:
        proof = ctx.signals.get("social_proof") or {}
        testi = proof.get("testimonials") or {}
        if testi.get("detected") or testi.get("potential"):
            rows.append(
                TrustSocialProofRow(
                    kind="Testimonial",
                    page_url=ctx.url,
                    evidence=str(testi.get("heading") or f"{testi.get('count') or 0} testimonial blocks"),
                    detected=bool(testi.get("detected")),
                    potential=bool(testi.get("potential")),
                )
            )
        reviews = proof.get("reviews") or {}
        if reviews.get("detected"):
            rows.append(
                TrustSocialProofRow(
                    kind="Review",
                    page_url=ctx.url,
                    evidence="Review markup" if reviews.get("schema") else "Review signals",
                    detected=True,
                )
            )
        cases = proof.get("case_studies") or {}
        if cases.get("detected"):
            rows.append(TrustSocialProofRow(kind="Case study", page_url=ctx.url, evidence="Case study wording", detected=True))
        logos = proof.get("client_logos") or {}
        if logos.get("detected") or logos.get("potential"):
            rows.append(
                TrustSocialProofRow(
                    kind="Client logos",
                    page_url=ctx.url,
                    evidence=str(logos.get("heading") or f"{logos.get('count') or 0} images"),
                    detected=bool(logos.get("detected")),
                    potential=bool(logos.get("potential")),
                )
            )
        awards = proof.get("awards") or {}
        if awards.get("detected"):
            labels = awards.get("labels") or ["Award"]
            rows.append(TrustSocialProofRow(kind="Award", page_url=ctx.url, evidence=str(labels[0]), detected=True))
    return rows[:40]


def _consistency_rows(site: SiteTrustContext) -> list[TrustConsistencyRow]:
    visible = first_name(site, "visible", "og", "header", "h1")
    schema = first_name(site, "schema", "organization_schema")
    footer = site.org_names.get("footer")
    about = site.org_names.get("about")
    from backend.analyzers.trust.checks._util import names_consistent

    overlap = names_consistent(visible, schema)
    if overlap is True:
        status = "Consistent"
    elif overlap is False:
        status = "Potential inconsistency"
    else:
        status = "Unavailable"
    return [
        TrustConsistencyRow(
            field="Organization name",
            visible=visible,
            schema_value=schema,
            footer=footer,
            about=about,
            status=status,
        )
    ]


def _security_rows(site: SiteTrustContext, checks) -> list[TrustSecurityRow]:
    rows = [
        TrustSecurityRow(
            signal="HTTPS",
            detected=site.https,
            evidence="HTTPS detected." if site.https else "HTTPS was not detected for the scanned URL.",
        )
    ]
    payments = []
    badges = []
    for ctx in site.pages:
        security = ctx.signals.get("security") or {}
        payments.extend(security.get("payment_brands") or [])
        badges.extend(security.get("badges") or [])
    rows.append(
        TrustSecurityRow(
            signal="Payment indicators",
            detected=bool(payments),
            evidence=", ".join(list(dict.fromkeys(payments))[:6]) if payments else "Not detected within crawl",
        )
    )
    rows.append(
        TrustSecurityRow(
            signal="Security badges",
            detected=bool(badges),
            evidence=", ".join(badges[:4]) if badges else "Not detected within crawl",
        )
    )
    privacy = bool(site.policies.get("privacy"))
    rows.append(
        TrustSecurityRow(
            signal="Privacy/security links",
            detected=privacy,
            evidence="Privacy policy page detected." if privacy else "Not detected within crawl",
        )
    )
    return rows


def analyze_trust(
    result: dict[str, Any] | None,
    *,
    pages: PagesPayload | None = None,
    current_year: int | None = None,
) -> TrustResult:
    payload = result or {}
    pages_payload = pages if pages is not None else payload_from_result(payload)
    crawled = [page for page in pages_payload.items if page.crawl_status == "crawled"]
    if not crawled:
        seed = next((page for page in pages_payload.items if page.is_seed), None)
        if seed is None:
            raise ScanError("TRUST_FAILED", "Trust & Credibility analysis could not be completed.")
        crawled = [seed]
    year = current_year if current_year is not None else datetime.now(timezone.utc).year
    site = build_contexts(crawled, payload, current_year=year)
    checks = _collect(site)
    page_infos: list[TrustPageInfo] = []
    for ctx in site.pages:
        page_checks = [item for item in checks if item.page_id == ctx.page.id]
        # Site-level checks attach to the seed; include them on the seed page score.
        if ctx.is_seed:
            scored = checks
        else:
            scored = page_checks or [item for item in checks if item.page_url == ctx.url]
        page_infos.append(
            TrustPageInfo(
                page_id=ctx.page.id,
                url=ctx.url,
                page_type=ctx.page_type,
                score=overall_score(scored) if ctx.is_seed else overall_score(page_checks) if page_checks else None,
                available=True,
                identity_status=actionable_status_safe(scored if ctx.is_seed else page_checks, "identity"),
                contact_status=actionable_status_safe(scored if ctx.is_seed else page_checks, "contact"),
                authorship_status=actionable_status_safe(page_checks, "authorship"),
                issue_count=sum(1 for item in (scored if ctx.is_seed else page_checks) if item.status in {"fail", "warning"}),
            )
        )
    signals, gaps = _signal_rows(checks)
    score = overall_score(checks)
    summary = summarize(checks, pages_analyzed=len(page_infos))
    return TrustResult(
        score=score,
        summary=summary,
        narrative=narrative_summary(score, summary),
        categories=category_scores(checks),
        category_cards=category_cards(checks),
        checks=checks,
        findings=checks,
        issues=collect_issues(checks),
        pages=page_infos,
        signals=signals,
        gaps=gaps,
        policies=_policy_rows(site),
        authors=_author_rows(site),
        social_proof=_social_rows(site),
        consistency=_consistency_rows(site),
        security=_security_rows(site, checks),
        methodology=METHODOLOGY,
        limitations=list(LIMITATIONS),
        score_note=SCORE_NOTE,
        crawl_note=CRAWL_NOTE,
    )
