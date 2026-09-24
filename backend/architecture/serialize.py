"""API shapes for Website Architecture."""

from __future__ import annotations

from typing import Any

from backend.architecture.config import MAX_DETAIL_NEIGHBORS, MAX_GRAPH_NODES, PAGE_TYPE_LABELS
from backend.architecture.engine import (
    ArchitectureGraph,
    NodeStats,
    collapse_edges,
    depth_distribution,
    insights_from_graph,
    neighbor_rows,
    node_to_dict,
    notes_from_graph,
    page_type_distribution,
    summary_from_graph,
    url_path_structure,
)
from backend.architecture.query import parse_graph_limit, select_graph_nodes, table_items
from backend.pages.models import InternalLink
from backend.services.url_identity import url_path, url_path_depth


def architecture_response(
    graph: ArchitectureGraph,
    *,
    scan_id: str,
    status: str | None,
    params: dict[str, Any],
    matching: list[NodeStats],
    paged: list[NodeStats],
    pagination: dict[str, int],
) -> dict[str, Any]:
    limit = parse_graph_limit(params.get("graph_limit"))
    focus = str(params.get("focus") or "").strip() or None
    pool = list(matching)
    if focus and all(node.page.id != focus for node in pool):
        extra = graph.nodes.get(focus)
        if extra is not None:
            pool = [extra, *pool]
    graph_nodes = select_graph_nodes(pool, limit=limit, focus_page_id=focus)
    allowed = {node.page.id for node in graph_nodes}
    shown = len(graph_nodes)
    matching_count = len(matching)
    limited = shown < matching_count
    payload_limits = graph.payload.limits or {}
    return {
        "scan_id": scan_id,
        "status": status,
        "in_progress": bool(graph.payload.in_progress),
        "summary": summary_from_graph(graph),
        "graph": {
            "shown": shown,
            "matching": matching_count,
            "total_pages": len(graph.nodes),
            "limited": limited,
            "limit": limit,
            "message": f"Showing {shown} of {matching_count} crawled pages." if limited else None,
        },
        "nodes": [node_to_dict(node) for node in graph_nodes],
        "edges": collapse_edges(graph.links, allowed),
        "items": table_items(paged),
        "pagination": pagination,
        "depth_distribution": depth_distribution(graph),
        "page_type_distribution": page_type_distribution(graph),
        "url_path_structure": url_path_structure(graph),
        "insights": insights_from_graph(graph),
        "notes": notes_from_graph(graph),
        "limits": {
            "max_pages": payload_limits.get("max_pages"),
            "max_depth": payload_limits.get("max_depth"),
            "max_graph_nodes": MAX_GRAPH_NODES,
        },
    }


def link_to_row(link: InternalLink, graph: ArchitectureGraph) -> dict[str, Any]:
    source = graph.nodes.get(link.source_page_id)
    dest = graph.nodes.get(link.destination_page_id)
    dest_type = dest.page.page_type if dest else None
    return {
        "id": link.id,
        "source_page_id": link.source_page_id,
        "destination_page_id": link.destination_page_id,
        "source_url": link.source_url,
        "destination_url": link.destination_url,
        "source_title": source.page.title if source else None,
        "destination_title": dest.page.title if dest else None,
        "source_path": url_path(source.page.normalized_url if source else link.source_url),
        "destination_path": url_path(dest.page.normalized_url if dest else link.destination_url),
        "anchor_text": link.anchor_text,
        "rel": link.rel,
        "destination_type": dest_type,
        "destination_type_label": (dest.page.page_type_label if dest else None)
        or PAGE_TYPE_LABELS.get((dest_type or "unknown").lower(), "Unknown"),
    }


def links_response(
    graph: ArchitectureGraph,
    *,
    scan_id: str,
    status: str | None,
    links: list[InternalLink],
    pagination: dict[str, int],
) -> dict[str, Any]:
    return {
        "scan_id": scan_id,
        "status": status,
        "items": [link_to_row(link, graph) for link in links],
        "pagination": pagination,
    }


def page_architecture_response(
    graph: ArchitectureGraph,
    node: NodeStats,
    *,
    scan_id: str,
    status: str | None,
) -> dict[str, Any]:
    inbound = node.inbound[:MAX_DETAIL_NEIGHBORS]
    outbound = node.outbound[:MAX_DETAIL_NEIGHBORS]
    page = node.page
    return {
        "scan_id": scan_id,
        "status": status,
        "page": {
            **node_to_dict(node),
            "canonical_url": page.canonical_url,
            "indexable": page.indexable,
            "word_count": page.word_count,
            "inbound_truncated": len(node.inbound) > MAX_DETAIL_NEIGHBORS,
            "outbound_truncated": len(node.outbound) > MAX_DETAIL_NEIGHBORS,
        },
        "architecture": {
            "crawl_depth": page.depth,
            "url_path_depth": url_path_depth(page.normalized_url or page.url),
            "inbound_internal_links": node.inbound_count,
            "outbound_internal_links": node.outbound_count,
            "potential_orphan": node.potential_orphan,
            "terminal_page": node.terminal_page,
            "dead_end": node.dead_end,
        },
        "inbound_links": neighbor_rows(inbound, graph, direction="inbound"),
        "outbound_links": neighbor_rows(outbound, graph, direction="outbound"),
        "notes": notes_from_graph(graph),
    }
