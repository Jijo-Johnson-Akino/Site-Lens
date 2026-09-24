"""Extract observable trust signals from already-fetched HTML. No HTTP, no verification."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
from bs4.element import Tag

from backend.analyzers.cro.extraction import PHONE_RE
from backend.analyzers.trust.config import (
    ABOUT_HREF,
    ABOUT_TEXT,
    AWARD_RE,
    CASE_STUDY_RE,
    CERT_RE,
    CITATION_RE,
    CLIENT_LOGO_HEADING,
    CLIENT_LOGO_MIN,
    CONTACT_HREF,
    CONTACT_TEXT,
    CONSUMER_EMAIL_DOMAINS,
    COPYRIGHT_RE,
    HOURS_RE,
    IDENTIFIER_RE,
    MAX_SIGNAL_ITEMS,
    PAYMENT_RE,
    POLICY_HREF,
    POLICY_TEXT,
    SECURE_WORDING,
    SOCIAL_DOMAINS,
    TESTIMONIAL_HEADING,
    TESTIMONIAL_QUOTE_MIN,
    USER_COUNT_RE,
)
from backend.analyzers.uiux.sanitizer import sanitize_selector, sanitize_text
from backend.parser.html_parser import EMAIL_RE, _is_hidden, parse_html
from backend.services.url_identity import hostname_of


def _text(tag: Tag | None, limit: int = 160) -> str:
    if tag is None:
        return ""
    return sanitize_text(tag.get_text(" ", strip=True), limit) or ""


def _visible(tag: Tag) -> bool:
    return not _is_hidden(tag)


def _blob(tag: Tag) -> str:
    classes = " ".join(tag.get("class") or [])
    ident = tag.get("id") or ""
    role = tag.get("role") or ""
    return f"{classes} {ident} {role}".lower()


def mask_email(value: str | None) -> str | None:
    if not value or "@" not in value:
        return value
    local, _, domain = value.partition("@")
    if len(local) <= 2:
        hidden = "*" * max(len(local), 1)
    else:
        hidden = local[:2] + "***"
    return f"{hidden}@{domain.lower()}"


def mask_phone(value: str | None) -> str | None:
    if not value:
        return value
    digits = re.sub(r"\D", "", value)
    if len(digits) < 4:
        return "••••"
    return f"••••{digits[-4:]}"


def email_domain(value: str | None) -> str | None:
    if not value or "@" not in value:
        return None
    return value.rsplit("@", 1)[-1].strip().lower() or None


def host_root(host: str | None) -> str:
    raw = (host or "").lower()
    if raw.startswith("www."):
        raw = raw[4:]
    return raw


def same_site_email(site_host: str | None, email: str | None) -> bool | None:
    domain = email_domain(email)
    root = host_root(site_host)
    mail = host_root(domain)
    if not root or not mail:
        return None
    return mail == root or mail.endswith("." + root) or root.endswith("." + mail)


def external_email_domain(site_host: str | None, email: str | None) -> bool:
    aligned = same_site_email(site_host, email)
    if aligned is True:
        return False
    domain = email_domain(email)
    if not domain:
        return False
    return True


def consumer_email(email: str | None) -> bool:
    domain = email_domain(email)
    return bool(domain and domain in CONSUMER_EMAIL_DOMAINS)


def social_platform(url: str) -> str | None:
    host = host_root(hostname_of(url) or urlsplit(url).hostname)
    if not host:
        return None
    if host in SOCIAL_DOMAINS:
        return SOCIAL_DOMAINS[host]
    for domain, label in SOCIAL_DOMAINS.items():
        root = host_root(domain)
        if host == root or host.endswith("." + root):
            return label
    return None


def classify_policy(href: str, text: str) -> str | None:
    blob = f"{href} {text}"
    for key, pattern in POLICY_HREF.items():
        if pattern.search(href) or POLICY_TEXT[key].search(text) or POLICY_TEXT[key].search(blob):
            if key == "terms" and POLICY_HREF["privacy"].search(href) and "privacy" in text.lower():
                continue
            return key
    return None


def looks_like_about(href: str, text: str) -> bool:
    return bool(ABOUT_HREF.search(href) or ABOUT_TEXT.search(text))


def looks_like_contact(href: str, text: str) -> bool:
    return bool(CONTACT_HREF.search(href) or CONTACT_TEXT.search(text))


def trust_page_type(page_type: str | None, url: str) -> str:
    path = (urlsplit(url).path or "/").lower()
    if any(part in path for part in ("/privacy", "/terms", "/cookie", "/refund", "/return", "/disclaimer", "/legal")):
        return "policy"
    if any(part in path for part in ("/about", "/team", "/our-story", "/company", "/who-we-are")):
        return "about"
    if any(part in path for part in ("/contact", "/support", "/help")):
        return "contact"
    if any(part in path for part in ("/pricing", "/plans", "/plan")):
        return "pricing"
    if any(part in path for part in ("/login", "/signin", "/sign-in", "/signup", "/register")):
        return "login"
    kind = (page_type or "unknown").lower()
    if kind in {"signup", "login"}:
        return "login"
    if kind == "blog":
        return "article"
    return kind or "unknown"


def _logo_present(soup: BeautifulSoup, parsed: dict[str, Any]) -> bool:
    for entity in ((parsed.get("json_ld") or {}).get("entities") or []):
        if entity.get("logo"):
            return True
    header = soup.find("header")
    scopes = [header, soup.find("nav"), soup]
    for scope in scopes:
        if not isinstance(scope, Tag) and scope is not soup:
            continue
        root = scope if isinstance(scope, Tag) else soup
        for image in root.find_all("img"):
            if not isinstance(image, Tag) or not _visible(image):
                continue
            alt = str(image.get("alt") or "")
            blob = _blob(image)
            src = str(image.get("src") or "")
            if "logo" in alt.lower() or "logo" in blob or "logo" in src.lower():
                return True
            if isinstance(scope, Tag) and scope.name == "header":
                return True
    return False


def _footer_name(footer: Tag | None) -> str | None:
    if not isinstance(footer, Tag):
        return None
    for heading in footer.find_all(["strong", "b", "p", "span", "a"]):
        if not isinstance(heading, Tag):
            continue
        text = _text(heading, 80)
        if text and 2 < len(text) <= 80 and "©" not in text and "copyright" not in text.lower():
            if heading.name in {"strong", "b"} or "brand" in _blob(heading) or "company" in _blob(heading):
                return text
    copyright_el = footer.find(string=COPYRIGHT_RE)
    if copyright_el:
        parent = copyright_el.parent if isinstance(copyright_el.parent, Tag) else footer
        blob = _text(parent if isinstance(parent, Tag) else footer, 160)
        cleaned = COPYRIGHT_RE.sub("", blob).strip(" -–—|,")
        if 2 < len(cleaned) <= 80:
            return cleaned
    return None


def _section_heading(tag: Tag) -> str:
    heading = tag.find(["h1", "h2", "h3", "h4"])
    if isinstance(heading, Tag):
        return _text(heading, 120)
    previous = tag.find_previous(["h1", "h2", "h3", "h4"])
    return _text(previous, 120) if isinstance(previous, Tag) else ""


def _testimonial_block(tag: Tag) -> bool:
    blob = _blob(tag)
    if any(token in blob for token in ("testimonial", "review", "quote", "customer-story")):
        return True
    heading = _section_heading(tag)
    return bool(TESTIMONIAL_HEADING.search(heading))


def extract_signals(html: str, page_url: str, parsed: dict[str, Any] | None = None) -> dict[str, Any]:
    soup = BeautifulSoup(html or "", "html.parser")
    html_data = parsed if isinstance(parsed, dict) else parse_html(html or "")
    visible = str(html_data.get("visible_text") or soup.get_text(" ", strip=True) or "")[:8000]
    footer = soup.find("footer")
    header = soup.find("header")
    json_ld = html_data.get("json_ld") if isinstance(html_data.get("json_ld"), dict) else {}
    entities = list(json_ld.get("entities") or [])
    types = [str(item) for item in (json_ld.get("types") or [])]

    schema_names: list[dict[str, Any]] = []
    schema_authors: list[str] = []
    schema_dates: list[str] = []
    schema_emails: list[str] = []
    schema_phones: list[str] = []
    schema_address = False
    same_as: list[str] = []
    publisher = None
    for entity in entities:
        ent_types = entity.get("types") or []
        name = entity.get("name")
        if name and isinstance(name, str):
            schema_names.append({"name": name.strip(), "types": list(ent_types)})
        if entity.get("author"):
            schema_authors.append(str(entity["author"]))
        if "Person" in ent_types and entity.get("name"):
            schema_authors.append(str(entity["name"]))
        if entity.get("datePublished"):
            schema_dates.append(str(entity["datePublished"]))
        if entity.get("dateModified"):
            schema_dates.append(str(entity["dateModified"]))
        if entity.get("email"):
            schema_emails.append(str(entity["email"]))
        if entity.get("telephone"):
            schema_phones.append(str(entity["telephone"]))
        if entity.get("address"):
            schema_address = True
        for item in entity.get("sameAs") or []:
            if isinstance(item, str) and item.strip():
                same_as.append(item.strip())
        if "WebSite" in ent_types or "Organization" in ent_types:
            if name:
                publisher = name

    emails = list(html_data.get("emails") or [])
    emails.extend(EMAIL_RE.findall(visible)[:8])
    emails.extend(schema_emails)
    mailto = list(html_data.get("mailto_links") or [])
    for item in mailto:
        href = str(item)
        if href.lower().startswith("mailto:"):
            emails.append(href.split(":", 1)[-1].split("?", 1)[0])
    unique_emails: list[str] = []
    seen_e: set[str] = set()
    for email in emails:
        key = email.strip().lower()
        if key and key not in seen_e and "@" in key:
            seen_e.add(key)
            unique_emails.append(email.strip())
        if len(unique_emails) >= 8:
            break

    phones = [str(item) for item in (html_data.get("tel_links") or [])]
    phones.extend(schema_phones)
    phones.extend(PHONE_RE.findall(visible)[:6])
    unique_phones: list[str] = []
    seen_p: set[str] = set()
    for phone in phones:
        raw = phone.strip()
        digits = re.sub(r"\D", "", raw)
        if digits.startswith("00"):
            digits = digits[2:]
        if len(digits) < 7:
            continue
        if digits in seen_p:
            continue
        seen_p.add(digits)
        unique_phones.append(raw)
        if len(unique_phones) >= 6:
            break

    address_el = soup.find("address")
    address_text = _text(address_el, 220) if isinstance(address_el, Tag) else None
    if not address_text:
        footer_text = _text(footer, 400) if isinstance(footer, Tag) else ""
        if re.search(r"\b(\d{3,6}|\b(?:street|st\.|road|rd\.|avenue|ave\.|suite|city)\b)", footer_text, re.I):
            if re.search(r"\d", footer_text) and re.search(r"[A-Za-z]{3,}", footer_text):
                address_text = footer_text[:220]
    has_address = bool(html_data.get("has_address") or address_text or schema_address)

    contact_links: list[dict[str, str]] = []
    about_links: list[dict[str, str]] = []
    policy_links: dict[str, list[dict[str, str]]] = {key: [] for key in POLICY_HREF}
    social_profiles: list[dict[str, str]] = []
    support_links: list[dict[str, str]] = []
    seen_social: set[str] = set()
    for link in html_data.get("links") or []:
        if not isinstance(link, dict):
            continue
        href = str(link.get("href") or "").strip()
        text = str(link.get("text") or "").strip()
        if not href:
            continue
        absolute = urljoin(page_url, href)
        lowered = href.lower()
        if looks_like_about(lowered, text) and len(about_links) < 8:
            about_links.append({"href": absolute[:240], "text": sanitize_text(text, 80) or "About"})
        if looks_like_contact(lowered, text) and len(contact_links) < 8:
            contact_links.append({"href": absolute[:240], "text": sanitize_text(text, 80) or "Contact"})
            if "support" in lowered or "help" in lowered or "support" in text.lower():
                support_links.append({"href": absolute[:240], "text": sanitize_text(text, 80) or "Support"})
        policy_key = classify_policy(lowered, text)
        if policy_key and len(policy_links[policy_key]) < 4:
            policy_links[policy_key].append({"href": absolute[:240], "text": sanitize_text(text, 80) or policy_key})
        platform = social_platform(absolute)
        if platform:
            host = host_root(hostname_of(absolute))
            key = f"{platform}:{host}"
            if key not in seen_social:
                seen_social.add(key)
                social_profiles.append({"platform": platform, "host": host or platform})
        if len(social_profiles) >= 12:
            break

    form_present = int(html_data.get("form_count") or 0) > 0
    if not form_present:
        form_present = bool(soup.find("form"))

    authors: list[str] = []
    for key in ("byline", "author_rel"):
        value = html_data.get(key)
        if value:
            authors.append(str(value))
    for rel in soup.find_all(attrs={"rel": True}):
        if not isinstance(rel, Tag):
            continue
        rels = rel.get("rel") or []
        rel_list = rels if isinstance(rels, list) else [rels]
        if any(str(item).lower() == "author" for item in rel_list):
            label = _text(rel, 80)
            if label:
                authors.append(label)
    for meta in soup.find_all("meta"):
        if not isinstance(meta, Tag):
            continue
        name = str(meta.get("name") or meta.get("property") or "").lower()
        if name in {"author", "article:author", "og:article:author"}:
            content = meta.get("content")
            if isinstance(content, str) and content.strip():
                authors.append(content.strip())
    authors.extend(schema_authors)
    unique_authors: list[str] = []
    seen_a: set[str] = set()
    for name in authors:
        key = name.strip().lower()
        if key and key not in seen_a:
            seen_a.add(key)
            unique_authors.append(name.strip())
        if len(unique_authors) >= 8:
            break

    dates = [str(item) for item in (html_data.get("time_values") or [])]
    dates.extend(schema_dates)
    for meta in soup.find_all("meta"):
        if not isinstance(meta, Tag):
            continue
        name = str(meta.get("name") or meta.get("property") or "").lower()
        if name in {"article:published_time", "article:modified_time", "og:updated_time", "date", "pubdate"}:
            content = meta.get("content")
            if isinstance(content, str) and content.strip():
                dates.append(content.strip())
    unique_dates: list[str] = []
    seen_d: set[str] = set()
    for value in dates:
        key = value.strip()
        if key and key not in seen_d:
            seen_d.add(key)
            unique_dates.append(key)
        if len(unique_dates) >= 8:
            break
    published = next((item for item in unique_dates if "modif" not in item.lower()), unique_dates[0] if unique_dates else None)
    modified = next((item for item in unique_dates if "modif" in item.lower() or "updated" in item.lower()), None)
    if not modified and len(unique_dates) > 1:
        modified = unique_dates[1]

    quotes = [tag for tag in soup.find_all("blockquote") if isinstance(tag, Tag) and _visible(tag)]
    testimonial_sections = 0
    testimonial_heading = None
    testimonial_potential = False
    for section in soup.find_all(["section", "div", "aside", "ul"]):
        if not isinstance(section, Tag) or not _visible(section):
            continue
        heading = _section_heading(section)
        blob = _blob(section)
        if TESTIMONIAL_HEADING.search(heading) or any(token in blob for token in ("testimonial", "reviews", "customer-story")):
            count = len(section.find_all(["blockquote", "li", "article", "figure"]))
            if count >= TESTIMONIAL_QUOTE_MIN or quotes:
                testimonial_sections += 1
                testimonial_heading = heading or testimonial_heading
            else:
                testimonial_potential = True
        if testimonial_sections >= 6:
            break
    if quotes and not testimonial_sections:
        testimonial_sections = len(quotes)
        testimonial_potential = testimonial_sections < TESTIMONIAL_QUOTE_MIN

    client_heading = None
    client_count = 0
    client_potential = False
    for section in soup.find_all(["section", "div", "aside", "ul"]):
        if not isinstance(section, Tag) or not _visible(section):
            continue
        heading = _section_heading(section)
        blob = _blob(section)
        if CLIENT_LOGO_HEADING.search(heading) or "logo-grid" in blob or "client-logos" in blob or "partners" in blob:
            images = [img for img in section.find_all("img") if isinstance(img, Tag) and _visible(img)]
            client_heading = heading or client_heading
            client_count = max(client_count, len(images))
            if len(images) < CLIENT_LOGO_MIN:
                client_potential = True
        if client_count >= 12:
            break

    case_detected = bool(CASE_STUDY_RE.search(visible))
    if not case_detected:
        for link in html_data.get("links") or []:
            if not isinstance(link, dict):
                continue
            blob = f"{link.get('href') or ''} {link.get('text') or ''}"
            if CASE_STUDY_RE.search(blob):
                case_detected = True
                break

    award_labels: list[str] = []
    cert_labels: list[str] = []
    for image in soup.find_all("img"):
        if not isinstance(image, Tag) or not _visible(image):
            continue
        alt = str(image.get("alt") or "")
        blob = f"{alt} {_blob(image)} {image.get('src') or ''}"
        if AWARD_RE.search(blob) and len(award_labels) < 6:
            award_labels.append(sanitize_text(alt or "Award badge", 80) or "Award badge")
        if CERT_RE.search(blob) and len(cert_labels) < 6:
            cert_labels.append(sanitize_text(alt or "Certification badge", 80) or "Certification badge")
    if AWARD_RE.search(visible) and not award_labels:
        award_labels.append("Award wording detected")
    if CERT_RE.search(visible) and not cert_labels:
        cert_labels.append("Certification wording detected")

    payment_brands: list[str] = []
    seen_pay: set[str] = set()
    for match in PAYMENT_RE.finditer(visible):
        label = match.group(0).strip()
        key = label.lower()
        if key not in seen_pay:
            seen_pay.add(key)
            payment_brands.append(label.title() if label.islower() else label)
        if len(payment_brands) >= 8:
            break
    for image in soup.find_all("img"):
        if not isinstance(image, Tag):
            continue
        blob = f"{image.get('alt') or ''} {image.get('src') or ''} {_blob(image)}"
        found = PAYMENT_RE.search(blob)
        if found:
            label = found.group(0)
            key = label.lower()
            if key not in seen_pay:
                seen_pay.add(key)
                payment_brands.append(label)
        if len(payment_brands) >= 8:
            break

    security_badges: list[str] = []
    for image in soup.find_all("img"):
        if not isinstance(image, Tag):
            continue
        blob = f"{image.get('alt') or ''} {_blob(image)} {image.get('src') or ''}"
        if re.search(r"\b(ssl|secure|norton|mcafee|trustpilot|security\s*badge)\b", blob, re.I):
            security_badges.append(sanitize_text(str(image.get("alt") or "Security badge"), 80) or "Security badge")
        if len(security_badges) >= 6:
            break
    secure_wording = bool(SECURE_WORDING.search(visible))

    hours: list[str] = []
    if HOURS_RE.search(visible):
        snippet = None
        match = HOURS_RE.search(visible)
        if match:
            start = max(0, match.start() - 10)
            snippet = sanitize_text(visible[start : match.end() + 40], 120)
        hours.append(snippet or "Business hours wording detected")

    identifiers: list[str] = []
    for match in IDENTIFIER_RE.finditer(visible):
        identifiers.append(sanitize_text(match.group(0), 80) or match.group(0)[:80])
        if len(identifiers) >= 4:
            break

    copyright_years: list[int] = []
    for match in COPYRIGHT_RE.finditer(visible):
        try:
            year = int(match.group(1))
        except (TypeError, ValueError):
            continue
        if year not in copyright_years:
            copyright_years.append(year)

    user_claims: list[str] = []
    for match in USER_COUNT_RE.finditer(visible):
        user_claims.append(sanitize_text(match.group(0), 80) or match.group(0))
        if len(user_claims) >= 3:
            break

    citations = bool(soup.find("cite")) or bool(CITATION_RE.search(visible))
    methodology = bool(re.search(r"methodology|editorial (policy|guidelines)", visible, re.I))
    pricing_link = any(
        isinstance(link, dict) and re.search(r"pricing|plans", f"{link.get('href') or ''} {link.get('text') or ''}", re.I)
        for link in (html_data.get("links") or [])
    )

    visible_name = None
    header_name = html_data.get("header_identity")
    og_name = html_data.get("og_site_name")
    footer_name = _footer_name(footer if isinstance(footer, Tag) else None)
    h1s = html_data.get("h1s") or []
    first_h1 = next((item.get("text") for item in h1s if isinstance(item, dict) and item.get("text")), None)
    for candidate in (og_name, header_name, footer_name, first_h1, html_data.get("title")):
        if candidate and str(candidate).strip():
            visible_name = str(candidate).strip()
            break

    https = (urlsplit(page_url).scheme or "").lower() == "https"

    return {
        "identity": {
            "visible_name": sanitize_text(visible_name, 80) if visible_name else None,
            "header_name": sanitize_text(str(header_name), 80) if header_name else None,
            "footer_name": sanitize_text(footer_name, 80) if footer_name else None,
            "og_site_name": sanitize_text(str(og_name), 80) if og_name else None,
            "h1": sanitize_text(str(first_h1), 80) if first_h1 else None,
            "logo": _logo_present(soup, html_data),
            "schema_names": schema_names[:8],
            "schema_types": types[:20],
            "publisher": sanitize_text(str(publisher), 80) if publisher else None,
            "same_as": same_as[:8],
        },
        "contact": {
            "emails": unique_emails,
            "phones": unique_phones,
            "address_text": address_text,
            "has_address": has_address,
            "form": form_present,
            "links": contact_links[:8],
            "support_links": support_links[:6],
        },
        "about": {"links": about_links[:8]},
        "policies": {key: value[:4] for key, value in policy_links.items()},
        "authorship": {
            "authors": unique_authors,
            "schema_authors": list(dict.fromkeys(schema_authors))[:8],
            "dates": unique_dates,
            "published": published,
            "modified": modified,
        },
        "social_proof": {
            "testimonials": {
                "detected": testimonial_sections >= TESTIMONIAL_QUOTE_MIN or bool(quotes),
                "count": max(testimonial_sections, len(quotes)),
                "heading": testimonial_heading,
                "potential": testimonial_potential and testimonial_sections < TESTIMONIAL_QUOTE_MIN,
            },
            "reviews": {
                "detected": bool({"Review", "AggregateRating"} & set(types)) or bool(TESTIMONIAL_HEADING.search(visible) and "review" in visible.lower()),
                "schema": bool({"Review", "AggregateRating"} & set(types)),
            },
            "case_studies": {"detected": case_detected},
            "client_logos": {
                "detected": client_count >= CLIENT_LOGO_MIN,
                "count": client_count,
                "heading": client_heading,
                "potential": client_potential or (bool(client_heading) and client_count < CLIENT_LOGO_MIN),
            },
            "user_claims": user_claims[:3],
            "awards": {"detected": bool(award_labels), "labels": award_labels[:6]},
        },
        "credentials": {
            "certifications": {"detected": bool(cert_labels), "labels": cert_labels[:6]},
            "awards": {"detected": bool(award_labels), "labels": award_labels[:6]},
        },
        "business": {
            "address": address_text,
            "hours": hours[:3],
            "identifiers": identifiers[:4],
            "schema_address": schema_address,
        },
        "security": {
            "https": https,
            "payment_brands": payment_brands[:8],
            "badges": security_badges[:6],
            "secure_wording": secure_wording,
        },
        "social": {"profiles": social_profiles[:12]},
        "footer": {
            "company_name": sanitize_text(footer_name, 80) if footer_name else None,
            "copyright_years": copyright_years[:4],
            "has_privacy": bool(policy_links.get("privacy")),
            "has_terms": bool(policy_links.get("terms")),
        },
        "transparency": {
            "citations": citations,
            "methodology": methodology,
            "pricing_link": bool(pricing_link),
        },
        "selector_hint": sanitize_selector("footer") if isinstance(footer, Tag) else sanitize_selector("header") if isinstance(header, Tag) else None,
        "capped": False,
        "max_items": MAX_SIGNAL_ITEMS,
    }


def merge_schema_entities(signals: dict[str, Any], entities: list[dict[str, Any]]) -> dict[str, Any]:
    """Reuse Phase 10 structured-data entities. Does not parse JSON-LD."""
    if not entities:
        return signals
    identity = dict(signals.get("identity") or {})
    names = list(identity.get("schema_names") or [])
    types = list(identity.get("schema_types") or [])
    contact = dict(signals.get("contact") or {})
    emails = list(contact.get("emails") or [])
    phones = list(contact.get("phones") or [])
    authorship = dict(signals.get("authorship") or {})
    authors = list(authorship.get("schema_authors") or [])
    dates = list(authorship.get("dates") or [])
    business = dict(signals.get("business") or {})
    hours = list(business.get("hours") or [])
    social_proof = dict(signals.get("social_proof") or {})
    reviews = dict(social_proof.get("reviews") or {})
    for entity in entities:
        ent_types = [str(item) for item in (entity.get("types") or [])]
        types.extend(ent_types)
        name = entity.get("name")
        if name:
            names.append({"name": str(name), "types": ent_types})
        props = entity.get("properties") if isinstance(entity.get("properties"), dict) else {}
        if props.get("email"):
            emails.append(str(props["email"]))
        if props.get("telephone"):
            phones.append(str(props["telephone"]))
        if props.get("author"):
            authors.append(str(props["author"]))
        if props.get("datePublished"):
            dates.append(str(props["datePublished"]))
        if props.get("dateModified"):
            dates.append(str(props["dateModified"]))
        if props.get("openingHours") or props.get("openingHoursSpecification"):
            hours.append(str(props.get("openingHours") or props.get("openingHoursSpecification")))
        if props.get("address"):
            business["schema_address"] = True
            if not business.get("address"):
                business["address"] = sanitize_text(str(props["address"]), 160)
        if "AggregateRating" in ent_types or "Review" in ent_types or props.get("aggregateRating") or props.get("review"):
            reviews["detected"] = True
            reviews["schema"] = True
        if props.get("sameAs"):
            identity["same_as"] = list(dict.fromkeys((identity.get("same_as") or []) + [str(props["sameAs"])]))[:8]
    identity["schema_names"] = names[:12]
    identity["schema_types"] = list(dict.fromkeys(types))[:24]
    contact["emails"] = list(dict.fromkeys(emails))[:8]
    contact["phones"] = list(dict.fromkeys(phones))[:6]
    authorship["schema_authors"] = list(dict.fromkeys(authors))[:8]
    authorship["dates"] = list(dict.fromkeys(dates))[:8]
    business["hours"] = hours[:4]
    social_proof["reviews"] = reviews
    signals["identity"] = identity
    signals["contact"] = contact
    signals["authorship"] = authorship
    signals["business"] = business
    signals["social_proof"] = social_proof
    return signals


def merge_content_signals(signals: dict[str, Any], content: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(content, dict):
        return signals
    payload_signals = content.get("signals") if isinstance(content.get("signals"), dict) else content
    authorship = dict(signals.get("authorship") or {})
    authors = list(authorship.get("authors") or [])
    summary = content.get("summary") if isinstance(content.get("summary"), dict) else {}
    if payload_signals.get("author_detected") or summary.get("author_detected"):
        for check in content.get("checks") or content.get("findings") or []:
            if not isinstance(check, dict):
                continue
            if str(check.get("check_id") or "") == "CONTENT-AUTH-001" and check.get("detected"):
                authors.append(str(check["detected"]))
    dates = list(authorship.get("dates") or [])
    if payload_signals.get("publication_date_detected") or summary.get("publication_date_detected"):
        for check in content.get("checks") or content.get("findings") or []:
            if not isinstance(check, dict):
                continue
            if str(check.get("check_id") or "") == "CONTENT-FRESH-001" and check.get("detected"):
                dates.append(str(check["detected"]))
    authorship["authors"] = list(dict.fromkeys(authors))[:8]
    authorship["dates"] = list(dict.fromkeys(dates))[:8]
    signals["authorship"] = authorship
    return signals


def merge_cro_contact(signals: dict[str, Any], cro_signals: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(cro_signals, dict):
        return signals
    contact = dict(signals.get("contact") or {})
    cro_contact = cro_signals.get("contact") if isinstance(cro_signals.get("contact"), dict) else {}
    emails = list(contact.get("emails") or [])
    for item in cro_contact.get("emails") or []:
        if item and str(item) not in emails:
            emails.append(str(item))
    phones = list(contact.get("phones") or [])
    for item in cro_contact.get("phones") or []:
        if item and str(item) not in phones:
            phones.append(str(item))
    contact["emails"] = emails[:8]
    contact["phones"] = phones[:6]
    if cro_contact.get("form"):
        contact["form"] = True
    signals["contact"] = contact
    return signals
