"""Extract observable CRO signals from already-fetched HTML. No HTTP, no form submit."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
from bs4.element import Tag

from backend.analyzers.cro.config import CTA_TEXT_MIN_LENGTH, MAX_CTAS, MAX_FORMS, PRIMARY_CTA_MIN_CONFIDENCE
from backend.analyzers.uiux.sanitizer import sanitize_selector, sanitize_text
from backend.parser.html_parser import _is_hidden
from backend.services.url_identity import hostname_of

CTA_PATTERN = re.compile(
    r"\b("
    r"get started|start free|start your|sign up|signup|book (a )?demo|contact us|"
    r"request (a )?demo|buy now|purchase|subscribe|learn more|get (a )?quote|"
    r"request (a )?quote|try now|try (it )?free|apply now|download|register|schedule|"
    r"talk to sales|create account|request quote|book now|shop now|"
    r"start trial|free trial|get in touch"
    r")\b",
    re.I,
)
STRONG_INTENT = re.compile(
    r"\b(start free|free trial|sign up|signup|buy now|purchase|book (a )?demo|"
    r"get (a )?quote|request (a )?quote|contact us|create account|register|subscribe|"
    r"talk to sales|apply now|try now|try (it )?free|schedule)\b",
    re.I,
)
VAGUE_CTA = re.compile(r"^(click here|submit|continue|more|next|here|click|go)$", re.I)
GENERIC_HEADING = re.compile(r"^(welcome|home|hello|hi there|untitled|page)$", re.I)
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
PRICE_RE = re.compile(r"(?:USD|EUR|GBP|\$|€|£)\s?\d[\d,]*(?:\.\d+)?|\b\d+\s?/\s?(?:mo|month|yr|year)\b", re.I)
TRUST_RE = re.compile(
    r"\b(testimonial|trusted by|case study|reviews?|guarantee|certified|ssl|secure checkout|"
    r"client logos?|as featured)\b",
    re.I,
)
PLAN_RE = re.compile(r"\b(pricing|plans?|packages?|per month|\/mo|tier)\b", re.I)

HIDDEN_INPUT = frozenset({"hidden", "submit", "button", "image", "reset", "file"})


def _text(tag: Tag | None, limit: int = 160) -> str:
    if tag is None:
        return ""
    return sanitize_text(tag.get_text(" ", strip=True), limit) or ""


def _visible(tag: Tag) -> bool:
    return not _is_hidden(tag)


def classify_destination(href: str | None, page_url: str) -> str:
    raw = (href or "").strip()
    if not raw or raw == "#":
        return "unknown"
    lowered = raw.lower()
    if lowered.startswith("javascript:"):
        return "unknown"
    if lowered.startswith("mailto:"):
        return "contact"
    if lowered.startswith("tel:"):
        return "contact"
    absolute = urljoin(page_url, raw)
    parsed = urlsplit(absolute)
    path = (parsed.path or "/").lower()
    if any(part in path for part in ("/signup", "/register", "/trial", "/get-started", "/start")):
        return "signup"
    if any(part in path for part in ("/contact", "/get-in-touch", "/support")):
        return "contact"
    if any(part in path for part in ("/pricing", "/plans", "/plan")):
        return "pricing"
    if any(part in path for part in ("/book", "/demo", "/schedule", "/booking")):
        return "booking"
    if any(part in path for part in ("/checkout", "/cart", "/buy", "/order")):
        return "checkout"
    host = hostname_of(absolute)
    page_host = hostname_of(page_url)
    if host and page_host and host != page_host:
        return "external"
    if parsed.scheme in {"http", "https"} or raw.startswith("/"):
        return "internal"
    return "unknown"


def broken_href(href: str | None) -> bool:
    raw = (href or "").strip()
    if not raw:
        return True
    lowered = raw.lower()
    return lowered in {"#", "javascript:void(0)", "javascript:;"} or lowered.startswith("javascript:")


def cro_page_type(page_type: str | None, url: str) -> str:
    path = (urlsplit(url).path or "/").lower()
    if "/pricing" in path or "/plans" in path:
        return "pricing"
    if page_type:
        return page_type
    return "unknown"


def infer_form_purpose(blob: str) -> str:
    text = blob.lower()
    if any(token in text for token in ("contact", "message", "get in touch", "enquiry", "inquiry")):
        return "contact"
    if any(token in text for token in ("sign up", "signup", "register", "create account")):
        return "signup"
    if any(token in text for token in ("log in", "login", "sign in", "password")):
        return "login"
    if "search" in text:
        return "search"
    if any(token in text for token in ("newsletter", "subscribe")):
        return "newsletter"
    return "unknown"


def cta_confidence(*, text: str, kind: str, in_viewport: bool | None, area: float = 0) -> int:
    score = 0
    if CTA_PATTERN.search(text or ""):
        score += 3
    if STRONG_INTENT.search(text or ""):
        score += 2
    if in_viewport:
        score += 2
    if kind in {"button", "submit"}:
        score += 1
    if area >= 2400:
        score += 1
    return score


def extract_signals(html: str, page_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html or "", "html.parser")
    h1 = soup.find("h1")
    h1_text = _text(h1, 180)
    supporting = ""
    root = h1.parent if h1 and isinstance(h1.parent, Tag) else soup
    for para in root.find_all("p"):
        if not isinstance(para, Tag) or not _visible(para):
            continue
        supporting = _text(para, 240)
        if len(supporting) >= 40:
            break
    if not supporting:
        for para in soup.find_all("p"):
            if isinstance(para, Tag) and _visible(para):
                supporting = _text(para, 240)
                if supporting:
                    break

    ctas: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_cta(tag: Tag, kind: str) -> None:
        if len(ctas) >= MAX_CTAS:
            return
        if not _visible(tag):
            return
        label = _text(tag, 80)
        if tag.name == "input":
            label = sanitize_text(str(tag.get("value") or tag.get("aria-label") or label), 80) or ""
        if not label:
            label = sanitize_text(str(tag.get("aria-label") or ""), 80) or ""
        if kind != "submit" and 0 < len(label.strip()) < CTA_TEXT_MIN_LENGTH and not VAGUE_CTA.match(label.strip()):
            return
        href = tag.get("href") if tag.name == "a" else None
        if isinstance(href, list):
            href = href[0] if href else None
        href_text = str(href).strip() if isinstance(href, str) else None
        key = f"{kind}|{label.lower()}|{href_text or ''}"
        if key in seen:
            return
        matched = bool(CTA_PATTERN.search(label) or VAGUE_CTA.match(label.strip()))
        if not matched and kind != "submit":
            return
        seen.add(key)
        dest = classify_destination(href_text, page_url) if href_text is not None or kind == "link" else ("form" if kind == "submit" else "unknown")
        if kind == "submit":
            dest = "form"
        conf = cta_confidence(text=label, kind=kind, in_viewport=None)
        ctas.append(
            {
                "text": label,
                "kind": kind,
                "href": (urljoin(page_url, href_text) if href_text and not href_text.lower().startswith(("javascript:", "mailto:", "tel:")) else href_text),
                "destination": dest,
                "broken": broken_href(href_text) if kind == "link" else False,
                "disabled": bool(tag.has_attr("disabled") or str(tag.get("aria-disabled") or "").lower() == "true"),
                "vague": bool(VAGUE_CTA.match(label.strip())),
                "strong": bool(STRONG_INTENT.search(label)),
                "confidence": conf,
                "selector": sanitize_selector(tag.name),
                "primary_candidate": conf >= PRIMARY_CTA_MIN_CONFIDENCE,
            }
        )

    for tag in soup.find_all(["a", "button", "input"]):
        if not isinstance(tag, Tag):
            continue
        name = (tag.name or "").lower()
        type_name = str(tag.get("type") or "").lower()
        if name == "input" and type_name not in {"submit", "button"}:
            continue
        if name == "a":
            add_cta(tag, "link")
        elif name == "input" and type_name == "submit":
            add_cta(tag, "submit")
        else:
            add_cta(tag, "button")

    forms: list[dict[str, Any]] = []
    for form in soup.find_all("form"):
        if not isinstance(form, Tag) or len(forms) >= MAX_FORMS:
            break
        fields: list[dict[str, Any]] = []
        for field in form.find_all(["input", "textarea", "select"]):
            if not isinstance(field, Tag) or not _visible(field):
                continue
            type_name = str(field.get("type") or field.name or "text").lower()
            if type_name in HIDDEN_INPUT:
                continue
            ident = str(field.get("id") or "")
            labeled = False
            if ident:
                labeled = bool(soup.find("label", attrs={"for": ident}))
            if not labeled:
                labeled = bool(field.find_parent("label") or field.get("aria-label") or field.get("aria-labelledby"))
            placeholder_only = bool(field.get("placeholder")) and not labeled
            fields.append(
                {
                    "type": type_name,
                    "name": sanitize_text(str(field.get("name") or field.get("id") or ""), 40),
                    "labeled": labeled,
                    "placeholder_only": placeholder_only,
                    "required": field.has_attr("required") or str(field.get("aria-required") or "").lower() == "true",
                }
            )
        submit = form.find(["button", "input"], attrs={"type": "submit"}) or form.find("button")
        submit_text = ""
        if isinstance(submit, Tag):
            submit_text = _text(submit, 80) or sanitize_text(str(submit.get("value") or ""), 80) or ""
        heading = form.find_previous(["h1", "h2", "h3", "legend"])
        purpose = infer_form_purpose(" ".join(filter(None, [_text(heading, 80), _text(form, 200), submit_text])))
        forms.append(
            {
                "selector": sanitize_selector("form"),
                "fields": len(fields),
                "field_details": fields[:20],
                "submit_text": submit_text or None,
                "purpose": purpose,
                "placeholder_only": sum(1 for item in fields if item["placeholder_only"]),
                "unlabeled": sum(1 for item in fields if not item["labeled"]),
                "required": sum(1 for item in fields if item["required"]),
                "has_email": any(item["type"] == "email" or (item["name"] or "").lower() == "email" for item in fields),
                "has_phone": any("tel" in item["type"] or "phone" in (item["name"] or "").lower() for item in fields),
                "has_password": any(item["type"] == "password" for item in fields),
            }
        )

    body_text = soup.get_text(" ", strip=True)[:4000]
    emails = EMAIL_RE.findall(body_text)[:3]
    phones = [item.strip() for item in PHONE_RE.findall(body_text)[:3]]
    contact_links = []
    for anchor in soup.find_all("a"):
        if not isinstance(anchor, Tag):
            continue
        href = anchor.get("href")
        href_text = str(href).strip() if isinstance(href, str) else ""
        label = _text(anchor, 80)
        dest = classify_destination(href_text, page_url)
        if dest == "contact" or "contact" in label.lower():
            contact_links.append({"text": label, "href": href_text[:180], "destination": dest})
        if len(contact_links) >= 6:
            break

    trust = []
    if TRUST_RE.search(body_text):
        trust.append({"kind": "copy", "text": "Trust-related wording detected near page copy."})
    logos = soup.select("[class*='logo' i], [class*='client' i], [class*='testimonial' i]")
    if logos:
        trust.append({"kind": "element", "count": min(len(logos), 12)})

    return {
        "h1": h1_text or None,
        "h1_present": bool(h1_text),
        "supporting_text": supporting or None,
        "generic_h1": bool(h1_text and GENERIC_HEADING.match(h1_text.strip())),
        "ctas": ctas,
        "forms": forms,
        "contact": {
            "emails": emails,
            "phones": phones,
            "links": contact_links,
            "form": any(item["purpose"] == "contact" for item in forms),
        },
        "pricing": {
            "price_text": bool(PRICE_RE.search(body_text)),
            "plan_text": bool(PLAN_RE.search(body_text)),
            "quote_cta": any(
                item["destination"] in {"contact", "pricing", "signup", "checkout", "booking"}
                or "quote" in (item["text"] or "").lower()
                or "trial" in (item["text"] or "").lower()
                for item in ctas
            ),
        },
        "trust": trust,
        "same_site_host": hostname_of(page_url),
    }


def merge_viewport_ctas(signals: dict[str, Any], viewport: dict[str, Any], *, viewport_name: str) -> list[dict[str, Any]]:
    """Overlay UI/UX rendered visibility onto HTML-detected CTAs without re-measuring the DOM."""
    rendered = []
    cta = viewport.get("cta") or {}
    for item in viewport.get("buttons") or []:
        rendered.append({**item, "kind": item.get("kind") or "button", "viewport": viewport_name})
    for item in viewport.get("links") or []:
        rendered.append({**item, "kind": item.get("kind") or "link", "viewport": viewport_name})
    by_text = {(str(item.get("text") or "").strip().lower()): item for item in rendered if item.get("text")}
    merged = []
    for cta_item in signals.get("ctas") or []:
        row = dict(cta_item)
        match = by_text.get(str(row.get("text") or "").strip().lower())
        if match:
            row["in_viewport"] = bool(match.get("in_viewport"))
            row["visible"] = bool(match.get("visible", True))
            row["clipped"] = bool(match.get("clipped"))
            row["disabled"] = bool(row.get("disabled") or match.get("disabled"))
            row["selector"] = match.get("selector") or row.get("selector")
            row["href"] = match.get("href") or row.get("href")
            if match.get("href"):
                row["destination"] = classify_destination(str(match.get("href")), signals.get("page_url") or "")
            area = float(match.get("width") or 0) * float(match.get("height") or 0)
            row["confidence"] = cta_confidence(
                text=str(row.get("text") or ""),
                kind=str(row.get("kind") or "link"),
                in_viewport=row.get("in_viewport"),
                area=area,
            )
            row["primary_candidate"] = int(row["confidence"]) >= PRIMARY_CTA_MIN_CONFIDENCE
        merged.append(row)
    if cta.get("exists") and cta.get("text"):
        needle = str(cta.get("text") or "").strip().lower()
        if needle and needle not in {str(item.get("text") or "").strip().lower() for item in merged}:
            merged.append(
                {
                    "text": cta.get("text"),
                    "kind": "button",
                    "href": None,
                    "destination": "unknown",
                    "broken": False,
                    "disabled": False,
                    "vague": bool(VAGUE_CTA.match(str(cta.get("text") or "").strip())),
                    "strong": bool(STRONG_INTENT.search(str(cta.get("text") or ""))),
                    "confidence": 4 if cta.get("in_viewport") else 2,
                    "selector": cta.get("selector"),
                    "primary_candidate": False,
                    "in_viewport": bool(cta.get("in_viewport")),
                    "visible": bool(cta.get("visible")),
                    "clipped": bool(cta.get("clipped")),
                    "potential": True,
                }
            )
    return merged
