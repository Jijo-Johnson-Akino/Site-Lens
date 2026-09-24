from __future__ import annotations

from backend.analyzers.content.config import DEFAULT_SCORING, ContentScoringConfig
from backend.analyzers.content.extract import ExtractedPage, snippet, word_count
from backend.analyzers.content.models import CheckResult, ContentPageType, make_check
from backend.analyzers.content.readability import measure_readability
from backend.analyzers.content.similarity import fingerprint, similarity


def page_url(page: ExtractedPage) -> str:
    return page.url


def content_check(page: ExtractedPage, **kwargs) -> CheckResult:
    return make_check(page_url=page_url(page), **kwargs)


SHORT_TYPES = {"login", "signup", "search", "contact", "application"}
ARTICLE_TYPES = {"article", "blog"}
ACTION_TYPES = {"homepage", "product", "service", "signup", "contact"}
AUTHOR_DATE_TYPES = {"article", "blog"}


def run_structure(page: ExtractedPage, page_type: ContentPageType, config: ContentScoringConfig) -> list[CheckResult]:
    checks: list[CheckResult] = []
    if page.main_detected:
        checks.append(content_check(page, check_id="CONTENT-STRUCTURE-001", name="Main content area", group="structure", status="pass", severity="medium", message="A main or article content area was detected.", why="Semantic main/article regions help separate primary copy from chrome.", detected="main/article"))
    elif page.word_count >= 40:
        checks.append(content_check(page, check_id="CONTENT-STRUCTURE-001", name="Main content area", group="structure", status="warning", severity="low", message="No semantic main/article landmark was found. Visible body text was used as a fallback.", recommendation="Wrap primary copy in main or article when it represents the page body.", why="Landmarks make primary content easier to isolate from navigation and footer chrome."))
    elif page_type.type in SHORT_TYPES or page.image_count >= 3:
        checks.append(content_check(page, check_id="CONTENT-STRUCTURE-001", name="Main content area", group="structure", status="not_applicable", severity="low", message="A distinct main content landmark is not required for this short or visual page type."))
    else:
        checks.append(content_check(page, check_id="CONTENT-STRUCTURE-001", name="Main content area", group="structure", status="warning", severity="medium", message="Little visible textual content was found and no main content area was detected.", detected=f"{page.word_count} words"))

    single_sentence = sum(1 for item in page.headings if item["following_words"] <= 8 and item["level"] <= 3)
    if page.word_count < 30 and page_type.type not in SHORT_TYPES and page.image_count < 3:
        checks.append(content_check(page, check_id="CONTENT-STRUCTURE-002", name="Meaningful text", group="structure", status="warning", severity="medium", message="The page contains almost no visible textual content.", detected=f"{page.word_count} words"))
    elif page.section_count >= 6 and single_sentence >= 5 and page.word_count < 250:
        checks.append(content_check(page, check_id="CONTENT-STRUCTURE-002", name="Meaningful text", group="structure", status="warning", severity="low", message="Several sections contain very little textual content.", detected=f"{single_sentence} short sections"))
    else:
        checks.append(content_check(page, check_id="CONTENT-STRUCTURE-002", name="Meaningful text", group="structure", status="pass", severity="low", message="Visible text is grouped into readable sections where headings exist." if page.headings else "Visible text was extracted from the page body."))

    ratio = 0.0
    boiler_words = word_count(page.boilerplate_text)
    if page.word_count:
        ratio = min(1.0, boiler_words / page.word_count)
    if page.word_count < 40:
        checks.append(content_check(page, check_id="CONTENT-BOIL-001", name="Boilerplate ratio", group="structure", status="not_applicable", severity="info", message="Not enough text was present to estimate boilerplate versus primary content."))
    elif ratio >= config.boilerplate_warn:
        checks.append(content_check(page, check_id="CONTENT-BOIL-001", name="Boilerplate ratio", group="structure", status="warning", severity="low", message=f"About {ratio:.0%} of extracted text appears in navigation, footer, or similar chrome.", recommendation="This is an estimate of site chrome versus primary copy, not a judgment that boilerplate is bad.", detected=f"{ratio:.0%}", details={"boilerplate_words": boiler_words, "visible_words": page.word_count}))
    else:
        checks.append(content_check(page, check_id="CONTENT-BOIL-001", name="Boilerplate ratio", group="structure", status="pass", severity="info", message=f"Primary copy appears to outweigh navigation/footer chrome ({ratio:.0%} boilerplate estimate).", detected=f"{ratio:.0%}"))

    list_count = len(page.lists)
    if list_count or page.table_count:
        checks.append(content_check(page, check_id="CONTENT-LIST-001", name="Lists and tables", group="structure", status="pass", severity="info", message=f"The page includes {list_count} content list(s) and {page.table_count} table(s).", detected=f"lists={list_count} tables={page.table_count}"))
    else:
        checks.append(content_check(page, check_id="CONTENT-LIST-001", name="Lists and tables", group="structure", status="pass", severity="info", message="No content lists or tables were required. Their absence is not a failure."))
    return checks


def run_depth(page: ExtractedPage, page_type: ContentPageType, config: ContentScoringConfig) -> list[CheckResult]:
    words = page.main_word_count or page.word_count
    if page_type.type in SHORT_TYPES:
        return [content_check(page, check_id="CONTENT-DEPTH-001", name="Content depth", group="depth", status="not_applicable", severity="low", message=f"Low word count is expected for a {page_type.type} page and is not treated as thin content.", detected=f"{words} words")]
    if page.image_count >= 4 and words < config.low_depth_words:
        return [content_check(page, check_id="CONTENT-DEPTH-001", name="Content depth", group="depth", status="not_applicable", severity="low", message="This page looks image-led. Word count alone is not used as a thin-content failure.", detected=f"{words} words, {page.image_count} images")]
    if words < config.thin_words:
        return [content_check(page, check_id="CONTENT-DEPTH-001", name="Content depth", group="depth", status="warning", severity="medium", message="Low visible word count detected.", recommendation="Add substantive copy if this page is meant to explain a topic. Short utility pages can ignore this signal.", detected=f"{words} words", details={"threshold": config.thin_words})]
    if words < config.low_depth_words and page_type.type in AUTHOR_DATE_TYPES | {"about", "unknown", "homepage"}:
        return [content_check(page, check_id="CONTENT-DEPTH-001", name="Content depth", group="depth", status="warning", severity="low", message="Several sections may have limited textual depth based on visible word count.", detected=f"{words} words")]
    return [content_check(page, check_id="CONTENT-DEPTH-001", name="Content depth", group="depth", status="pass", severity="low", message=f"Visible word count is {words}. Word count alone does not mean the content is high quality.", detected=f"{words} words")]


def run_readability(page: ExtractedPage, page_type: ContentPageType, config: ContentScoringConfig) -> list[CheckResult]:
    result = measure_readability(page.main_text or page.visible_text, page.language)
    if not result.supported or result.flesch_reading_ease is None:
        return [content_check(page, check_id="CONTENT-READ-001", name="Readability", group="readability", status="not_applicable", severity="low", message=result.reason or "Readability formula not applied because the detected language is not supported.", detected=page.language or "unknown")]
    ease = result.flesch_reading_ease
    grade = result.flesch_kincaid_grade
    detected = f"Flesch {ease}; grade {grade}"
    if ease <= config.read_very_difficult:
        status, severity = "warning", "medium"
        message = f"Content readability is very difficult according to Flesch Reading Ease ({ease}). The calculated readability level is approximately grade {grade}."
    elif ease <= config.read_difficult:
        status, severity = "warning", "low"
        message = f"Content readability is difficult according to the selected formula ({ease}, {result.label}). The calculated readability level is approximately grade {grade}."
    else:
        status, severity = "pass", "low"
        message = f"Flesch Reading Ease is {ease} ({result.label}). The calculated readability level is approximately grade {grade}."
    return [content_check(page, check_id="CONTENT-READ-001", name="Readability", group="readability", status=status, severity=severity, message=message, detected=detected, why="Readability formulas are statistical signals for English text. They do not judge accuracy or quality.")]


def run_headings(page: ExtractedPage, page_type: ContentPageType, config: ContentScoringConfig) -> list[CheckResult]:
    headings = page.headings
    checks: list[CheckResult] = []
    long_heads = [item for item in headings if len(item.get("text") or "") >= config.long_heading_chars]
    if long_heads:
        checks.append(content_check(page, check_id="CONTENT-HEAD-001", name="Heading length", group="headings", status="warning", severity="low", message="Very long heading detected.", detected=snippet(long_heads[0]["text"]), affected_element_count=len(long_heads), selector="h1,h2,h3"))
    elif headings:
        checks.append(content_check(page, check_id="CONTENT-HEAD-001", name="Heading length", group="headings", status="pass", severity="low", message="Headings are not excessively long."))
    else:
        checks.append(content_check(page, check_id="CONTENT-HEAD-001", name="Heading length", group="headings", status="not_applicable", severity="low", message="No headings were present to evaluate length."))

    empty = [item for item in headings if item.get("empty")]
    if empty:
        checks.append(content_check(page, check_id="CONTENT-HEAD-002", name="Empty headings", group="headings", status="warning", severity="medium", message=f"{len(empty)} empty heading(s) were found.", affected_element_count=len(empty), selector="h1,h2,h3"))
    elif headings:
        checks.append(content_check(page, check_id="CONTENT-HEAD-002", name="Empty headings", group="headings", status="pass", severity="low", message="No empty headings were detected."))
    else:
        checks.append(content_check(page, check_id="CONTENT-HEAD-002", name="Empty headings", group="headings", status="not_applicable", severity="low", message="No headings were present."))

    texts = [(item.get("text") or "").strip().lower() for item in headings if item.get("text")]
    repeated_headings = sum(1 for text in set(texts) if texts.count(text) >= 2)
    if repeated_headings:
        checks.append(content_check(page, check_id="CONTENT-HEAD-003", name="Repeated headings", group="headings", status="warning", severity="low", message="Repeated headings appear on the page.", affected_element_count=repeated_headings))
    else:
        checks.append(content_check(page, check_id="CONTENT-HEAD-003", name="Repeated headings", group="headings", status="pass" if headings else "not_applicable", severity="low", message="Headings are not heavily repeated." if headings else "No headings were present."))

    thin_h2 = [item for item in headings if item["level"] == 2 and item["following_words"] < 5 and page_type.type in AUTHOR_DATE_TYPES]
    if thin_h2 and page.word_count >= 200:
        checks.append(content_check(page, check_id="CONTENT-HEAD-004", name="Heading-to-content relationship", group="headings", status="warning", severity="low", message="Some headings have very little following textual content.", affected_element_count=len(thin_h2)))
    elif headings:
        checks.append(content_check(page, check_id="CONTENT-HEAD-004", name="Heading-to-content relationship", group="headings", status="pass", severity="low", message="Headings appear to organize following content."))
    else:
        if page_type.type in SHORT_TYPES:
            checks.append(content_check(page, check_id="CONTENT-HEAD-004", name="Heading-to-content relationship", group="headings", status="not_applicable", severity="low", message="Heading structure is not required for this page type."))
        else:
            checks.append(content_check(page, check_id="CONTENT-HEAD-004", name="Heading-to-content relationship", group="headings", status="warning", severity="low", message="No headings were found to organize the content."))
    return checks


def run_paragraphs(page: ExtractedPage, page_type: ContentPageType, config: ContentScoringConfig) -> list[CheckResult]:
    paras = page.paragraphs
    long_paras = [item for item in paras if word_count(item) >= config.long_paragraph_words]
    if long_paras:
        checks = [content_check(page, check_id="CONTENT-PARA-001", name="Paragraph length", group="paragraphs", status="warning", severity="low", message="Very long paragraph detected.", detected=f"{word_count(long_paras[0])} words", affected_element_count=len(long_paras), selector="p")]
    elif paras:
        checks = [content_check(page, check_id="CONTENT-PARA-001", name="Paragraph length", group="paragraphs", status="pass", severity="low", message="Paragraphs are not extremely long.")]
    else:
        status = "not_applicable" if page_type.type in SHORT_TYPES else "warning"
        checks = [content_check(page, check_id="CONTENT-PARA-001", name="Paragraph length", group="paragraphs", status=status, severity="low", message="No paragraphs were detected." if status == "warning" else "Paragraphs are not required for this page type.")]

    short_runs = 0
    current = 0
    for item in paras:
        if word_count(item) <= 4:
            current += 1
            short_runs = max(short_runs, current)
        else:
            current = 0
    if short_runs >= 6:
        checks.append(content_check(page, check_id="CONTENT-PARA-002", name="Fragmented paragraphs", group="paragraphs", status="warning", severity="low", message="Excessive consecutive short paragraphs were detected.", detected=f"{short_runs} consecutive short paragraphs"))
    else:
        checks.append(content_check(page, check_id="CONTENT-PARA-002", name="Fragmented paragraphs", group="paragraphs", status="pass" if paras else "not_applicable", severity="low", message="Paragraphs are not excessively fragmented." if paras else "No paragraphs were present."))
    return checks


def run_duplication(page: ExtractedPage, page_type: ContentPageType, config: ContentScoringConfig, extra: list[ExtractedPage]) -> list[CheckResult]:
    from backend.analyzers.content.extract import repeated_blocks

    checks: list[CheckResult] = []
    if extra:
        pairs = []
        for other in extra[: config.max_dup_pages]:
            if other.url == page.url:
                continue
            exact = fingerprint(page.main_text) == fingerprint(other.main_text) and bool(page.main_text.strip())
            score = 1.0 if exact else similarity(page.main_text, other.main_text)
            pairs.append((other.url, score, exact))
        best = max(pairs, key=lambda item: item[1], default=None)
        if best and best[2]:
            checks.append(content_check(page, check_id="CONTENT-DUP-001", name="Duplicate content", group="duplication", status="warning", severity="medium", message="Very similar content detected across these pages.", detected=f"exact match with {best[0]}", details={"url": best[0], "similarity": 1.0, "kind": "exact"}))
        elif best and best[1] >= config.near_dup:
            checks.append(content_check(page, check_id="CONTENT-DUP-001", name="Duplicate content", group="duplication", status="warning", severity="medium", message="Very similar content detected across these pages.", detected=f"{best[1]:.0%} similar to {best[0]}", details={"url": best[0], "similarity": round(best[1], 3), "kind": "near"}))
        else:
            checks.append(content_check(page, check_id="CONTENT-DUP-001", name="Duplicate content", group="duplication", status="pass", severity="low", message="No exact or near-duplicate pages were detected among the compared pages."))
    else:
        checks.append(content_check(page, check_id="CONTENT-DUP-001", name="Duplicate content", group="duplication", status="not_applicable", severity="info", message="Site-wide duplicate analysis requires multiple crawled pages."))

    repeated, ratio, samples = repeated_blocks(page.paragraphs, page.headings)
    if repeated:
        checks.append(content_check(page, check_id="CONTENT-REP-001", name="Repeated content", group="duplication", status="warning", severity="medium", message="Repeated text appears across multiple sections.", detected=samples[0] if samples else f"ratio={ratio:.0%}", details={"ratio": round(ratio, 3), "samples": samples}))
    else:
        checks.append(content_check(page, check_id="CONTENT-REP-001", name="Repeated content", group="duplication", status="pass", severity="low", message="No repeated paragraph or heading blocks were detected in primary content."))
    return checks


def run_freshness(page: ExtractedPage, page_type: ContentPageType, config: ContentScoringConfig) -> list[CheckResult]:
    if page_type.type not in AUTHOR_DATE_TYPES:
        return [content_check(page, check_id="CONTENT-FRESH-001", name="Publication date", group="freshness", status="not_applicable", severity="info", message="Publication date is not required for this page type.")]
    if page.dates:
        return [content_check(page, check_id="CONTENT-FRESH-001", name="Publication date", group="freshness", status="pass", severity="low", message="A publication or modification date was detected.", detected=page.dates[0])]
    return [content_check(page, check_id="CONTENT-FRESH-001", name="Publication date", group="freshness", status="warning", severity="info", message="Publication date not detected on this article-like page.", recommendation="Missing dates are not proof that content is outdated.", why="Dates are an observable freshness signal, not an editorial quality score.")]


def run_authorship(page: ExtractedPage, page_type: ContentPageType, config: ContentScoringConfig) -> list[CheckResult]:
    if page_type.type not in AUTHOR_DATE_TYPES:
        return [content_check(page, check_id="CONTENT-AUTH-001", name="Authorship", group="authorship", status="not_applicable", severity="info", message="Author information is not required for this page type.")]
    if page.author_candidates:
        return [content_check(page, check_id="CONTENT-AUTH-001", name="Authorship", group="authorship", status="pass", severity="low", message="Author information was detected.", detected=", ".join(page.author_candidates[:3]))]
    return [content_check(page, check_id="CONTENT-AUTH-001", name="Authorship", group="authorship", status="warning", severity="medium", message="No visible author information was detected for this article-like page.")]


def run_completeness(page: ExtractedPage, page_type: ContentPageType, config: ContentScoringConfig) -> list[CheckResult]:
    kind = page_type.type
    html = page.parsed
    description = html.get("meta_description") or (page.paragraphs[0] if page.paragraphs else "")
    has_desc = bool(description and len(description) >= 40)
    has_contact = bool(html.get("emails") or html.get("mailto_links") or html.get("tel_links") or html.get("has_address") or page.has_form)
    about_link = any("about" in ((item.get("text") or "") + (item.get("href") or "")).lower() for item in page.links)
    missing: list[str] = []
    if kind == "homepage":
        if not has_desc:
            missing.append("a clear description of what the site does")
        if not has_contact and not about_link:
            missing.append("a contact or about signal")
    elif kind in {"product", "service"}:
        if page.word_count < 40:
            missing.append("a product or service description")
        if not page.lists and page.word_count < 80:
            missing.append("features or benefits in structured copy")
        if not page.cta_labels:
            missing.append("a contact or purchase action")
    elif kind in AUTHOR_DATE_TYPES:
        if not page.title:
            missing.append("a title")
        if len(page.paragraphs) < 2:
            missing.append("an introduction and body paragraphs")
        if sum(1 for item in page.headings if item["level"] == 2) < 1 and page.word_count > 200:
            missing.append("structured sections")
    elif kind == "contact":
        if not has_contact:
            missing.append("a contact method")
    elif kind == "about":
        if page.word_count < 80:
            missing.append("a meaningful organization or person description")
    if missing:
        return [content_check(page, check_id="CONTENT-COMP-001", name="Content completeness", group="completeness", status="warning", severity="low", message="Some expected content elements for this page type were not observed: " + ", ".join(missing) + ".", detected="; ".join(missing))]
    return [content_check(page, check_id="CONTENT-COMP-001", name="Content completeness", group="completeness", status="pass", severity="low", message=f"Observable content elements for a {kind} page are present." if kind != "unknown" else "Basic title and text signals are present.")]


def run_relationships(page: ExtractedPage, page_type: ContentPageType, extra_count: int) -> list[CheckResult]:
    if extra_count <= 0:
        site = content_check(page, check_id="CONTENT-LINK-001", name="Internal content relationships", group="relationships", status="not_applicable", severity="info", message="Site-wide relationship checks require multiple crawled pages. Contextual links on this page were still counted.", detected=f"{page.internal_content_links} in-content internal links")
        # Spec: If only one page is available, N/A for site-wide. Keep N/A.
        return [site]
    if page_type.type in SHORT_TYPES:
        return [content_check(page, check_id="CONTENT-LINK-001", name="Internal content relationships", group="relationships", status="not_applicable", severity="low", message="Contextual internal links are not required for this page type.")]
    if page.internal_content_links >= 2:
        return [content_check(page, check_id="CONTENT-LINK-001", name="Internal content relationships", group="relationships", status="pass", severity="low", message="The content includes internal links to related pages.", detected=str(page.internal_content_links))]
    return [content_check(page, check_id="CONTENT-LINK-001", name="Internal content relationships", group="relationships", status="warning", severity="low", message="Few contextual internal content links detected.", detected=str(page.internal_content_links))]


def run_language(page: ExtractedPage) -> list[CheckResult]:
    if page.language:
        return [content_check(page, check_id="CONTENT-LANG-001", name="Declared language", group="language", status="pass", severity="low", message=f"The document declares language `{page.language}`. This is not a claim that the text is correctly labeled.", detected=page.language)]
    if page.word_count < 20:
        return [content_check(page, check_id="CONTENT-LANG-001", name="Declared language", group="language", status="not_applicable", severity="low", message="Not enough text was present to evaluate language.")]
    return [content_check(page, check_id="CONTENT-LANG-001", name="Declared language", group="language", status="warning", severity="low", message="No html lang attribute was detected. English readability formulas are not applied without a supported language.")]


def run_cta(page: ExtractedPage, page_type: ContentPageType) -> list[CheckResult]:
    if page_type.type in AUTHOR_DATE_TYPES or page_type.type in {"about"}:
        if page.cta_labels:
            return [content_check(page, check_id="CONTENT-CTA-001", name="Calls to action", group="completeness", status="pass", severity="info", message="Primary action candidate detected.", detected=", ".join(page.cta_labels[:3]))]
        return [content_check(page, check_id="CONTENT-CTA-001", name="Calls to action", group="completeness", status="not_applicable", severity="info", message="No obvious primary action detected. Informational pages are not required to include a CTA.")]
    if page.cta_labels:
        return [content_check(page, check_id="CONTENT-CTA-001", name="Calls to action", group="completeness", status="pass", severity="low", message="Primary action candidate detected.", detected=", ".join(page.cta_labels[:3]))]
    if page_type.type in ACTION_TYPES or page_type.type == "unknown":
        return [content_check(page, check_id="CONTENT-CTA-001", name="Calls to action", group="completeness", status="warning", severity="info", message="No obvious primary action detected.", recommendation="This is an observational CTA signal, not a CRO score.")]
    return [content_check(page, check_id="CONTENT-CTA-001", name="Calls to action", group="completeness", status="not_applicable", severity="info", message="No obvious primary action detected.")]
