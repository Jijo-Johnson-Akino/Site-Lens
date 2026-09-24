from __future__ import annotations

import re

from backend.analyzers.aeo.checks._util import page_url
from backend.analyzers.aeo.context import AeoContext
from backend.analyzers.aeo.models import CheckResult, make_check

AI_CRAWLERS = (
    "GPTBot",
    "ChatGPT-User",
    "Google-Extended",
    "Google-CloudVertexBot",
    "anthropic-ai",
    "ClaudeBot",
    "Claude-Web",
    "PerplexityBot",
    "Bytespider",
    "CCBot",
    "Applebot-Extended",
    "cohere-ai",
    "meta-externalagent",
    "FacebookBot",
)

UA_RE = re.compile(r"(?im)^\s*user-agent\s*:\s*(.+?)\s*$")


def run(ctx: AeoContext) -> list[CheckResult]:
    page = page_url(ctx)
    return [_robots_ai(ctx, page), _llms_txt(ctx, page), _accessible_text(ctx, page)]


def _robots_ai(ctx: AeoContext, page: str) -> CheckResult:
    why = "This reports crawler names that appear in robots.txt. A directive does not guarantee inclusion or exclusion from any particular AI product."
    probe = ctx.robots_txt or {}
    body = probe.get("body") if isinstance(probe.get("body"), str) else None
    if not probe.get("exists") or body is None:
        return make_check(
            check_id="AEO-AI-001",
            name="robots.txt AI crawler references",
            group="extractability",
            status="not_applicable",
            severity="info",
            message="AI crawler directives were not evaluated because robots.txt was not retrieved.",
            why=why,
            page_url=page,
        )
    agents = [match.strip() for match in UA_RE.findall(body)]
    listed = []
    lower_body = body.lower()
    for name in AI_CRAWLERS:
        if name.lower() in lower_body:
            listed.append(name)
    if listed:
        return make_check(
            check_id="AEO-AI-001",
            name="robots.txt AI crawler references",
            group="extractability",
            status="pass",
            severity="info",
            message="robots.txt mentions one or more known AI-related crawler names.",
            recommendation="Review those groups to confirm they match the intended access policy. Directives are not a ranking guarantee.",
            why=why,
            detected=", ".join(listed) + f". User-agent lines: {len(agents)}.",
            page_url=page,
        )
    return make_check(
        check_id="AEO-AI-001",
        name="robots.txt AI crawler references",
        group="extractability",
        status="pass",
        severity="info",
        message="No AI-crawler-specific user-agent names were found in robots.txt.",
        why=why,
        detected=f"{len(agents)} user-agent line(s); none matched the known AI crawler list.",
        page_url=page,
    )


def _llms_txt(ctx: AeoContext, page: str) -> CheckResult:
    why = "llms.txt is an emerging convention for providing a machine-oriented summary. Absence is not a failure and does not mean the site is “not AI optimized.”"
    probe = ctx.llms_txt or {}
    status = probe.get("status_code")
    if probe.get("exists") and status == 200:
        body = (probe.get("body") or "").strip()
        preview = body.splitlines()[0][:120] if body else "empty file"
        return make_check(
            check_id="AEO-AI-002",
            name="llms.txt",
            group="extractability",
            status="pass",
            severity="info",
            message="An llms.txt file was detected at the site origin.",
            why=why,
            detected=f"HTTP 200. {preview}",
            page_url=page,
        )
    if status is None:
        return make_check(
            check_id="AEO-AI-002",
            name="llms.txt",
            group="extractability",
            status="warning",
            severity="info",
            message="The llms.txt request did not return an HTTP status (error).",
            why=why,
            detected="error",
            page_url=page,
        )
    if int(status) >= 500:
        return make_check(
            check_id="AEO-AI-002",
            name="llms.txt",
            group="extractability",
            status="warning",
            severity="info",
            message="The llms.txt request returned a server error.",
            why=why,
            detected=f"error HTTP {status}",
            page_url=page,
        )
    return make_check(
        check_id="AEO-AI-002",
        name="llms.txt",
        group="extractability",
        status="warning",
        severity="info",
        message="No llms.txt file was detected.",
        recommendation="Publishing /llms.txt is optional. Absence does not mean the website cannot be interpreted.",
        why=why,
        detected=f"not found HTTP {status}",
        page_url=page,
    )


def _accessible_text(ctx: AeoContext, page: str) -> CheckResult:
    why = "This checks whether the first HTML response contains readable text. It does not attempt to query any AI system."
    text_len = int(ctx.html.get("visible_text_length") or 0)
    if text_len >= 400:
        return make_check(
            check_id="AEO-AI-003",
            name="Accessible textual content",
            group="extractability",
            status="pass",
            severity="medium",
            message="Meaningful textual content is available in the initial response.",
            why=why,
            detected=f"{text_len} visible characters.",
            page_url=page,
        )
    if text_len >= 120:
        return make_check(
            check_id="AEO-AI-003",
            name="Accessible textual content",
            group="extractability",
            status="warning",
            severity="medium",
            message="Only a small amount of text is available in the initial response.",
            why=why,
            detected=f"{text_len} visible characters.",
            page_url=page,
        )
    return make_check(
        check_id="AEO-AI-003",
        name="Accessible textual content",
        group="extractability",
        status="fail",
        severity="medium",
        message="The initial HTML response does not expose meaningful textual content.",
        recommendation="Include primary copy in the HTML so non-scripted readers can use it.",
        why=why,
        detected=f"{text_len} visible characters.",
        page_url=page,
    )
