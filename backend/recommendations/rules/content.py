from backend.recommendations.registry import rule

RULES = [
    rule(
        "content.improve_thin_content",
        "Content",
        "Improve thin page content",
        "Add substantive copy on pages with low visible word count where the page type is expected to explain a topic.",
        "Low visible word count is a signal that a page may not explain its subject. Short utility pages can ignore this finding.",
        (
            "Review whether the affected page is meant to explain a topic.",
            "Add visible copy that covers the primary subject if the page is not a short utility view.",
            "Do not add filler text solely to increase word count.",
        ),
        ("content.thin_page",),
        effort="medium",
        impact="medium",
    ),
    rule(
        "content.improve_content_structure",
        "Content",
        "Improve content structure",
        "Add a main content area and headings that organize following copy.",
        "A main/article landmark and headings that introduce following text make primary content easier to isolate from chrome.",
        (
            "Wrap primary copy in main or article when it represents the page body.",
            "Add headings that introduce the following sections.",
            "Remove or fill empty headings.",
        ),
        ("content.structure.001", "content.head.002", "content.head.004"),
        effort="medium",
        impact="medium",
    ),
    rule(
        "content.review_duplicate_content",
        "Content",
        "Review duplicate or near-duplicate pages",
        "Review pages whose visible content is exact or near-duplicate of another crawled page.",
        "Very similar content across URLs can make pages harder to distinguish. Similarity is measured from crawled text, not from an editorial quality score.",
        (
            "Compare the listed pages and decide whether they should remain separate.",
            "Differentiate the copy if both URLs should stay published.",
            "Use canonical or consolidation options if one URL is the preferred version.",
        ),
        ("content.dup.001",),
        effort="medium",
        impact="medium",
    ),
    rule(
        "content.add_authorship",
        "Content",
        "Add authorship on article-like pages",
        "Add visible author information on article-like pages where none was detected.",
        "Author information is an observable identity signal for article-like pages. It is not required for every page type.",
        (
            "Add a visible byline on the affected article-like pages.",
            "Keep the byline consistent with any Article author markup.",
            "Do not add authorship on page types that are not article-like solely to clear this finding.",
        ),
        ("content.auth.001",),
        effort="small",
        impact="low",
    ),
]
