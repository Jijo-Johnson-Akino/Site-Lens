"""Architecture recommendations from crawled graph observations, not invented issues."""

from __future__ import annotations

from typing import Any

from backend.architecture.engine import ArchitectureGraph

ORPHAN_KEY = "architecture.improve_internal_linking"
DEEP_KEY = "architecture.review_internal_linking"
DEAD_END_KEY = "architecture.review_dead_end_pages"


def orphan_nodes(graph: ArchitectureGraph) -> list[Any]:
    if not graph.links_recorded:
        return []
    return [node for node in graph.nodes.values() if node.potential_orphan]


def deep_nodes(graph: ArchitectureGraph) -> list[Any]:
    if not graph.links_recorded:
        return []
    return [node for node in graph.nodes.values() if node.page.depth >= 3 and not node.page.is_seed]


def dead_end_nodes(graph: ArchitectureGraph) -> list[Any]:
    if not graph.links_recorded:
        return []
    return [node for node in graph.nodes.values() if node.dead_end]


def architecture_rule_copy(recommendation_key: str) -> dict[str, Any]:
    if recommendation_key == ORPHAN_KEY:
        return {
            "recommendation_key": ORPHAN_KEY,
            "category": "Architecture",
            "title": "Improve internal linking to pages with no inbound links",
            "summary": "Add internal links to crawled pages that currently have no inbound links in the observed graph.",
            "rationale": (
                "Potential orphan pages are pages with no inbound internal links within the crawled graph. "
                "Pages outside the crawl, blocked URLs, or unobserved links may not be represented."
            ),
            "action_steps": [
                "Review the listed pages in Website Architecture.",
                "Add internal links to those pages from relevant crawled pages.",
                "Confirm the new links are observable in HTML, not only in scripts that the crawl did not execute.",
            ],
            "effort": "medium",
            "impact": "medium",
            "priority": "medium",
        }
    if recommendation_key == DEEP_KEY:
        return {
            "recommendation_key": DEEP_KEY,
            "category": "Architecture",
            "title": "Review pages discovered at high crawl depth",
            "summary": "Review whether important pages discovered at crawl depth 3 or deeper should be reachable in fewer internal-link hops.",
            "rationale": (
                "Crawl depth is the discovery distance from the seed URL, not a ranking score. "
                "Pages at the configured crawl limit may still be important destinations."
            ),
            "action_steps": [
                "Review the listed pages and whether they should be closer to the homepage in the link graph.",
                "Add internal links from higher-level pages if those destinations are important.",
                "Treat this as a crawl-graph observation, not proof that users cannot find the pages.",
            ],
            "effort": "large",
            "impact": "low",
            "priority": "low",
        }
    return {
        "recommendation_key": DEAD_END_KEY,
        "category": "Architecture",
        "title": "Add outbound links from dead-end pages",
        "summary": "Add internal links from crawled pages that currently have no outbound internal links and are not typical terminal page types.",
        "rationale": (
            "Pages with no outbound internal links give crawlers and users no next step inside the crawled graph. "
            "Contact, login, and signup pages are treated as expected terminal types and are excluded."
        ),
        "action_steps": [
            "Review the listed pages in Website Architecture.",
            "Add contextual internal links to related pages where the content supports them.",
            "Do not add links solely to change the graph if the page is intentionally terminal.",
        ],
        "effort": "medium",
        "impact": "low",
        "priority": "low",
    }
