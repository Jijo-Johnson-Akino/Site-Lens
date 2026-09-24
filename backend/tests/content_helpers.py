from __future__ import annotations

from pathlib import Path

from backend.analyzers.content.analyzer import analyze_content
from backend.analyzers.content.config import ContentScoringConfig
from backend.analyzers.content.context import ContentContext, ExtraPage
from backend.analyzers.content.models import ContentResult
from backend.parser.html_parser import parse_html

FIXTURES = Path(__file__).parent / "fixtures" / "content"

SENTENCES = [
    "Visible word count is measured from extracted text after scripts and styles are removed.",
    "Headings organize the remaining paragraphs into sections that a reader can scan.",
    "SiteBench records paragraph counts without claiming the writing is universally good.",
    "A publication date is stored only when the markup actually contains one.",
    "Author names are collected from bylines, rel=author links, or Person structured data.",
    "Readability formulas estimate grade level for English sentences using syllable counts.",
    "Boilerplate estimates compare navigation and footer text with primary copy.",
    "Repeated blocks are found by normalizing whitespace and comparing paragraph fingerprints.",
    "Internal links inside the main region are counted separately from header menus.",
    "Calls to action are detected from button and link labels such as contact us.",
    "Thin content warnings use configurable thresholds rather than a single magic number.",
    "Contact pages are not penalized for missing article authors or dates.",
    "Product pages may include features, descriptions, and a purchase or inquiry action.",
    "Language detection starts with the html lang attribute declared on the document.",
    "Unsupported languages skip English Flesch calculations instead of inventing a score.",
    "Duplicate analysis compares extra crawled pages when the scan already collected them.",
    "This module does not fetch the public internet to look for plagiarism.",
    "Completeness checks look for observable elements that match the classified page type.",
    "Lists and tables are reported as structure signals and are never required on every page.",
    "Long paragraphs can make scanning harder, but length alone is not an automatic failure.",
]


def load_content_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def expand_sentences(count: int) -> list[str]:
    lines = []
    index = 0
    while len(lines) < count:
        base = SENTENCES[index % len(SENTENCES)]
        cycle = index // len(SENTENCES)
        if cycle:
            lines.append(f"{base} Additional detail {cycle} explains the same idea with new wording.")
        else:
            lines.append(base)
        index += 1
    return lines


def article_html(
    *,
    title: str = "How SiteBench measures content",
    lang: str = "en",
    author: str | None = "Jordan Blake",
    date: str | None = "2024-04-12",
    paragraphs: int = 24,
    cta: bool = False,
    extra_paragraph: str | None = None,
    path_hint: str = "/blog/content-analysis",
) -> str:
    body = expand_sentences(paragraphs)
    if extra_paragraph:
        body.append(extra_paragraph)
    paras = "\n".join(f"<p>{item}</p>" for item in body)
    author_html = f'<p class="byline">By {author}</p>' if author else ""
    date_html = f'<time datetime="{date}">{date}</time>' if date else ""
    cta_html = '<p><a href="/demo">Book a Demo</a></p>' if cta else ""
    schema = ""
    if author or date:
        props = ['"@type": "Article"', f'"headline": "{title}"']
        if author:
            props.append(f'"author": {{"@type": "Person", "name": "{author}"}}')
        if date:
            props.append(f'"datePublished": "{date}"')
        schema = "<script type=\"application/ld+json\">{" + ", ".join(props) + "}</script>"
    return f"""<!doctype html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <meta name="description" content="A long-form explanation of measurable content signals used by SiteBench.">
  <link rel="canonical" href="https://example.com{path_hint}">
  {schema}
</head>
<body>
  <header><nav><a href="/">Home</a><a href="/blog">Blog</a></nav></header>
  <main>
    <article>
      <h1>{title}</h1>
      {author_html}{date_html}
      <h2>What the analyzer measures</h2>
      {paras}
      <h2>How findings are reported</h2>
      <p>Findings describe measured structure, depth, and repetition rather than editorial taste.</p>
      <p>Related reading is available in the <a href="/blog/readability">readability notes</a> and the <a href="/blog/headings">heading guide</a>.</p>
      {cta_html}
    </article>
  </main>
  <footer><p>Copyright example.com</p></footer>
</body>
</html>
"""


def analyze_html(
    html: str,
    url: str = "https://example.com/blog/content-analysis",
    extra: list[tuple[str, str]] | None = None,
    config: ContentScoringConfig | None = None,
) -> ContentResult:
    extras = tuple(ExtraPage(url=item[0], html_source=item[1]) for item in (extra or []))
    return analyze_content(
        ContentContext(
            page_url=url,
            final_url=url,
            html=parse_html(html),
            html_source=html,
            extra_pages=extras,
        ),
        config=config,
    )


def by_id(result: ContentResult, check_id: str):
    return next(check for check in result.checks if check.check_id == check_id)
