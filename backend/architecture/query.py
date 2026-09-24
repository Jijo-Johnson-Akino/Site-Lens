"""Filter, search, sort, and paginate architecture nodes and links."""

from __future__ import annotations

from typing import Any

from backend.architecture.config import (
    DEFAULT_PAGE_SIZE,
    MAX_GRAPH_NODES,
    MAX_PAGE_SIZE,
    MAX_SEARCH_LENGTH,
    SORT_FIELDS,
    LINK_SORT_FIELDS,
)
from backend.architecture.engine import ArchitectureGraph, NodeStats, node_to_dict
from backend.pages.config import CRAWL_STATUS_FILTERS, PAGE_TYPE_FILTERS, TYPE_ALIASES
from backend.pages.models import InternalLink


def parse_page(raw: Any) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 1
    return max(1, value)


def parse_page_size(raw: Any) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_PAGE_SIZE
    return max(1, min(MAX_PAGE_SIZE, value))


def parse_search(raw: Any) -> str:
    text = str(raw or "")
    if len(text) > MAX_SEARCH_LENGTH:
        return text[:MAX_SEARCH_LENGTH]
    return text


def parse_sort(raw: Any) -> str:
    value = str(raw or "depth").strip().lower()
    aliases = {
        "inbound_link_count": "inbound",
        "outbound_link_count": "outbound",
        "issues": "issue_count",
        "status": "crawl_status",
        "type": "page_type",
        "crawl_depth": "depth",
    }
    mapped = aliases.get(value, value)
    return mapped if mapped in SORT_FIELDS else "depth"


def parse_link_sort(raw: Any) -> str:
    value = str(raw or "source").strip().lower()
    aliases = {"src": "source", "dest": "destination", "anchor_text": "anchor", "type": "destination_type"}
    mapped = aliases.get(value, value)
    return mapped if mapped in LINK_SORT_FIELDS else "source"


def parse_order(raw: Any, *, default: str = "asc") -> str:
    value = str(raw or default).strip().lower()
    return "asc" if value == "asc" else "desc"


def parse_page_type(raw: Any) -> str | None:
    if raw is None or str(raw).lower() in {"", "all"}:
        return None
    value = str(raw).strip().lower().replace("-", " ").replace("_", " ")
    compact = value.replace(" ", "")
    for item in PAGE_TYPE_FILTERS:
        if item == value or item.replace(" ", "") == compact:
            return item
    if compact in {"login/signup", "loginsignup"}:
        return "login"
    return None


def parse_crawl_status(raw: Any) -> str | None:
    if raw is None or str(raw).lower() in {"", "all"}:
        return None
    value = str(raw).strip().lower()
    return value if value in CRAWL_STATUS_FILTERS else None


def parse_has_issues(raw: Any) -> bool | None:
    if raw is None or str(raw).lower() in {"", "all"}:
        return None
    value = str(raw).strip().lower()
    if value in {"true", "1", "yes", "has_issues", "issues"}:
        return True
    if value in {"false", "0", "no", "none", "no_issues"}:
        return False
    return None


def parse_flag(raw: Any) -> bool | None:
    if raw is None or str(raw).lower() in {"", "all"}:
        return None
    value = str(raw).strip().lower()
    if value in {"true", "1", "yes"}:
        return True
    if value in {"false", "0", "no"}:
        return False
    return None


def parse_depth(raw: Any) -> int | str | None:
    if raw is None or str(raw).lower() in {"", "all"}:
        return None
    value = str(raw).strip().lower()
    if value == "unknown":
        return "unknown"
    try:
        return int(value)
    except ValueError:
        return None


def parse_graph_limit(raw: Any) -> int:
    if raw is None or str(raw).strip() == "":
        return MAX_GRAPH_NODES
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return MAX_GRAPH_NODES
    return max(1, min(MAX_GRAPH_NODES, value))


def _type_matches(node: NodeStats, needle: str) -> bool:
    actual = (node.page.page_type or "unknown").lower()
    aliases = TYPE_ALIASES.get(needle, frozenset({needle}))
    return actual in aliases


def filter_nodes(
    nodes: list[NodeStats],
    *,
    search: str = "",
    page_type: str | None = None,
    crawl_status: str | None = None,
    depth: int | str | None = None,
    has_issues: bool | None = None,
    orphan: bool | None = None,
    terminal: bool | None = None,
) -> list[NodeStats]:
    needle = search.strip().lower()
    selected: list[NodeStats] = []
    for node in nodes:
        page = node.page
        if page_type and not _type_matches(node, page_type):
            continue
        if crawl_status and page.crawl_status != crawl_status:
            continue
        if depth == "unknown" and page.depth is not None:
            continue
        if isinstance(depth, int) and page.depth != depth:
            continue
        if has_issues is True and page.issue_count <= 0:
            continue
        if has_issues is False and page.issue_count > 0:
            continue
        if orphan is True and not node.potential_orphan:
            continue
        if orphan is False and node.potential_orphan:
            continue
        if terminal is True and not node.terminal_page:
            continue
        if terminal is False and node.terminal_page:
            continue
        if needle:
            blob = " ".join(
                filter(
                    None,
                    [
                        page.url,
                        page.normalized_url,
                        page.final_url or "",
                        page.title or "",
                        page.h1 or "",
                    ],
                )
            ).lower()
            if needle not in blob:
                continue
        selected.append(node)
    return selected


def _sort_value(node: NodeStats, sort: str) -> Any:
    page = node.page
    if sort == "url":
        return (page.normalized_url or page.url).lower()
    if sort == "inbound":
        return node.inbound_count
    if sort == "outbound":
        return node.outbound_count
    if sort == "issue_count":
        return page.issue_count
    if sort == "page_type":
        return (page.page_type or "unknown").lower()
    if sort == "crawl_status":
        return page.crawl_status
    return page.depth if page.depth is not None else 10_000


def sort_nodes(nodes: list[NodeStats], sort: str, order: str) -> list[NodeStats]:
    reverse = order == "desc"

    def key(node: NodeStats) -> tuple:
        return (_sort_value(node, sort), node.inbound_count, (node.page.normalized_url or node.page.url).lower())

    return sorted(nodes, key=key, reverse=reverse)


def paginate(items: list, page: int, page_size: int) -> tuple[list, dict[str, int]]:
    total = len(items)
    pages = max(1, (total + page_size - 1) // page_size) if total else 1
    current = min(page, pages)
    start = (current - 1) * page_size
    end = start + page_size
    return items[start:end], {
        "page": current,
        "page_size": page_size,
        "total": total,
        "pages": pages,
        "total_pages": pages,
    }


def select_graph_nodes(
    nodes: list[NodeStats],
    *,
    limit: int,
    focus_page_id: str | None = None,
) -> list[NodeStats]:
    if len(nodes) <= limit:
        return list(nodes)
    chosen: list[NodeStats] = []
    seen: set[str] = set()

    def take(node: NodeStats | None) -> None:
        if node is None or node.page.id in seen or len(chosen) >= limit:
            return
        seen.add(node.page.id)
        chosen.append(node)

    by_id = {node.page.id: node for node in nodes}
    take(next((node for node in nodes if node.page.is_seed), None))
    if focus_page_id:
        take(by_id.get(focus_page_id))
    ranked = sorted(
        nodes,
        key=lambda node: (-node.inbound_count, node.page.depth, (node.page.normalized_url or node.page.url).lower()),
    )
    for node in ranked:
        take(node)
        if len(chosen) >= limit:
            break
    return chosen


def matching_nodes(graph: ArchitectureGraph, params: dict[str, Any]) -> list[NodeStats]:
    filtered = filter_nodes(
        list(graph.nodes.values()),
        search=parse_search(params.get("search")),
        page_type=parse_page_type(params.get("page_type")),
        crawl_status=parse_crawl_status(params.get("crawl_status")),
        depth=parse_depth(params.get("depth")),
        has_issues=parse_has_issues(params.get("has_issues")),
        orphan=parse_flag(params.get("orphan")),
        terminal=parse_flag(params.get("terminal")),
    )
    return sort_nodes(filtered, parse_sort(params.get("sort")), parse_order(params.get("order"), default="asc"))


def query_nodes(graph: ArchitectureGraph, params: dict[str, Any]) -> tuple[list[NodeStats], list[NodeStats], dict[str, int]]:
    sorted_items = matching_nodes(graph, params)
    paged, pagination = paginate(sorted_items, parse_page(params.get("page")), parse_page_size(params.get("page_size")))
    return sorted_items, paged, pagination


def filter_links(
    links: list[InternalLink],
    graph: ArchitectureGraph,
    *,
    search: str = "",
    source: str | None = None,
    destination: str | None = None,
) -> list[InternalLink]:
    needle = search.strip().lower()
    selected: list[InternalLink] = []
    for link in links:
        if source and source not in {link.source_page_id, link.source_url}:
            source_node = graph.nodes.get(link.source_page_id)
            if source_node is None or source not in {source_node.page.normalized_url, source_node.url_path}:
                continue
        if destination and destination not in {link.destination_page_id, link.destination_url}:
            dest_node = graph.nodes.get(link.destination_page_id)
            if dest_node is None or destination not in {dest_node.page.normalized_url, dest_node.url_path}:
                continue
        if needle:
            source_node = graph.nodes.get(link.source_page_id)
            dest_node = graph.nodes.get(link.destination_page_id)
            blob = " ".join(
                filter(
                    None,
                    [
                        link.source_url,
                        link.destination_url,
                        link.anchor_text or "",
                        (source_node.page.title if source_node else None) or "",
                        (dest_node.page.title if dest_node else None) or "",
                    ],
                )
            ).lower()
            if needle not in blob:
                continue
        selected.append(link)
    return selected


def sort_links(links: list[InternalLink], graph: ArchitectureGraph, sort: str, order: str) -> list[InternalLink]:
    reverse = order == "desc"

    def key(link: InternalLink) -> tuple:
        source = graph.nodes.get(link.source_page_id)
        dest = graph.nodes.get(link.destination_page_id)
        if sort == "destination":
            primary = (dest.page.normalized_url if dest else link.destination_url).lower()
        elif sort == "anchor":
            primary = (link.anchor_text or "").lower()
        elif sort == "destination_type":
            primary = ((dest.page.page_type if dest else None) or "unknown").lower()
        else:
            primary = (source.page.normalized_url if source else link.source_url).lower()
        return (primary, link.source_url.lower(), link.destination_url.lower())

    return sorted(links, key=key, reverse=reverse)


def query_links(graph: ArchitectureGraph, params: dict[str, Any]) -> tuple[list[InternalLink], dict[str, int]]:
    filtered = filter_links(
        graph.links,
        graph,
        search=parse_search(params.get("search")),
        source=str(params.get("source") or "").strip() or None,
        destination=str(params.get("destination") or "").strip() or None,
    )
    sorted_items = sort_links(
        filtered,
        graph,
        parse_link_sort(params.get("sort")),
        parse_order(params.get("order"), default="asc"),
    )
    return paginate(sorted_items, parse_page(params.get("page")), parse_page_size(params.get("page_size")))


def table_items(nodes: list[NodeStats]) -> list[dict[str, Any]]:
    return [node_to_dict(node) for node in nodes]
