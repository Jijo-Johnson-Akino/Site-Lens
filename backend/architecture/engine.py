"""Build architecture nodes and edges from persisted pages and internal links."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from backend.architecture.config import (
    DEPTH_NOTE,
    LINKS_NOTE,
    MAX_URL_TREE_NODES,
    METHODOLOGY,
    ORPHAN_NOTE,
    PAGE_TYPE_LABELS,
    TERMINAL_PAGE_TYPES,
)
from backend.pages.engine import payload_from_result
from backend.pages.models import InternalLink, PageRecord, PagesPayload
from backend.services.url_identity import url_path, url_path_depth


@dataclass
class NodeStats:
    page: PageRecord
    inbound: list[InternalLink] = field(default_factory=list)
    outbound: list[InternalLink] = field(default_factory=list)

    @property
    def inbound_count(self) -> int:
        return len(self.inbound)

    @property
    def outbound_count(self) -> int:
        return len(self.outbound)

    @property
    def url_path(self) -> str:
        return url_path(self.page.normalized_url or self.page.url)

    @property
    def url_path_depth(self) -> int:
        return url_path_depth(self.page.normalized_url or self.page.url)

    @property
    def potential_orphan(self) -> bool:
        return self.inbound_count == 0 and not self.page.is_seed

    @property
    def terminal_page(self) -> bool:
        kind = (self.page.page_type or "").lower()
        return self.outbound_count == 0 and kind in TERMINAL_PAGE_TYPES

    @property
    def dead_end(self) -> bool:
        return self.outbound_count == 0 and not self.terminal_page


@dataclass
class ArchitectureGraph:
    payload: PagesPayload
    nodes: dict[str, NodeStats]
    links: list[InternalLink]
    links_recorded: bool


def build_architecture(result: dict[str, Any] | PagesPayload | None) -> ArchitectureGraph:
    if isinstance(result, PagesPayload):
        payload = result
    else:
        payload = payload_from_result(result if isinstance(result, dict) else None)
    nodes = {page.id: NodeStats(page=page) for page in payload.items if page.id}
    links: list[InternalLink] = []
    seen: set[str] = set()
    scan_id = payload.items[0].scan_id if payload.items else None
    for link in payload.internal_links:
        if scan_id and link.scan_id and link.scan_id != scan_id:
            continue
        if link.source_page_id not in nodes or link.destination_page_id not in nodes:
            continue
        if link.source_page_id == link.destination_page_id:
            continue
        identity = f"{link.source_page_id}|{link.destination_page_id}|{(link.anchor_text or '').strip().lower()}"
        if identity in seen:
            continue
        seen.add(identity)
        links.append(link)
        nodes[link.source_page_id].outbound.append(link)
        nodes[link.destination_page_id].inbound.append(link)
    return ArchitectureGraph(
        payload=payload,
        nodes=nodes,
        links=links,
        links_recorded=payload.internal_links_recorded,
    )


def summary_from_graph(graph: ArchitectureGraph) -> dict[str, Any]:
    nodes = list(graph.nodes.values())
    depths = [node.page.depth for node in nodes if node.page.depth is not None]
    page_count = len(nodes)
    average = round(sum(depths) / len(depths), 1) if depths else None
    external = graph.payload.summary.external_links_discovered
    data: dict[str, Any] = {
        "page_count": page_count,
        "internal_link_count": len(graph.links),
        "max_crawl_depth": max(depths) if depths else None,
        "average_crawl_depth": average,
        "potential_orphan_count": sum(1 for node in nodes if node.potential_orphan),
        "dead_end_count": sum(1 for node in nodes if node.dead_end),
        "terminal_page_count": sum(1 for node in nodes if node.terminal_page),
        "no_outbound_count": sum(1 for node in nodes if node.outbound_count == 0),
        "links_recorded": graph.links_recorded,
    }
    if isinstance(external, int):
        data["external_links_discovered"] = external
    return data


def depth_distribution(graph: ArchitectureGraph) -> list[dict[str, int]]:
    counts: dict[int, int] = defaultdict(int)
    for node in graph.nodes.values():
        counts[node.page.depth] += 1
    return [{"depth": depth, "page_count": counts[depth]} for depth in sorted(counts)]


def page_type_distribution(graph: ArchitectureGraph) -> list[dict[str, Any]]:
    counts: dict[str, int] = defaultdict(int)
    for node in graph.nodes.values():
        kind = (node.page.page_type or "unknown").lower() or "unknown"
        counts[kind] += 1
    rows = []
    for kind, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        rows.append(
            {
                "page_type": kind,
                "label": PAGE_TYPE_LABELS.get(kind, kind.replace("_", " ").title()),
                "page_count": count,
            }
        )
    return rows


def url_path_structure(graph: ArchitectureGraph) -> dict[str, Any]:
    paths: dict[str, dict[str, Any]] = {}
    for node in graph.nodes.values():
        path = node.url_path
        entry = paths.setdefault(
            path,
            {
                "path": path,
                "url_path_depth": node.url_path_depth,
                "page_count": 0,
                "sample_title": None,
            },
        )
        entry["page_count"] += 1
        if not entry["sample_title"] and node.page.title:
            entry["sample_title"] = node.page.title
    rows = sorted(paths.values(), key=lambda item: (item["url_path_depth"], item["path"]))
    truncated = len(rows) > MAX_URL_TREE_NODES
    rows = rows[:MAX_URL_TREE_NODES]
    return {
        "groups": rows,
        "truncated": truncated,
        "note": "URL Path Structure groups crawled URLs by path. It is not a claim of true website hierarchy.",
    }


def insights_from_graph(graph: ArchitectureGraph) -> list[dict[str, str]]:
    summary = summary_from_graph(graph)
    items: list[dict[str, str]] = []
    orphans = summary["potential_orphan_count"]
    if orphans:
        items.append(
            {
                "id": "orphans",
                "text": f"{orphans} page{'s' if orphans != 1 else ''} {'have' if orphans != 1 else 'has'} no inbound internal links within the crawled graph.",
            }
        )
    no_out = summary["no_outbound_count"]
    if no_out:
        items.append(
            {
                "id": "no_outbound",
                "text": f"{no_out} page{'s' if no_out != 1 else ''} {'have' if no_out != 1 else 'has'} no outbound internal links.",
            }
        )
    terminals = summary["terminal_page_count"]
    if terminals:
        items.append(
            {
                "id": "terminal",
                "text": f"{terminals} page{'s' if terminals != 1 else ''} look like terminal page types with no outbound internal links.",
            }
        )
    for row in depth_distribution(graph):
        if row["depth"] >= 3:
            count = row["page_count"]
            items.append(
                {
                    "id": f"depth_{row['depth']}",
                    "text": f"{count} page{'s' if count != 1 else ''} {'are' if count != 1 else 'is'} at crawl depth {row['depth']}.",
                }
            )
    seed = next((node for node in graph.nodes.values() if node.page.is_seed), None)
    if seed and seed.outbound_count:
        title = (seed.page.title or "Homepage").strip() or "Homepage"
        items.append(
            {
                "id": "seed_outbound",
                "text": f"{title} contains {seed.outbound_count} outbound internal link{'s' if seed.outbound_count != 1 else ''}.",
            }
        )
    return items[:12]


def notes_from_graph(graph: ArchitectureGraph) -> list[str]:
    notes = [METHODOLOGY, ORPHAN_NOTE, LINKS_NOTE, DEPTH_NOTE]
    if graph.payload.summary.depth_limit_reached:
        notes.append("Pages beyond configured crawl depth were not analyzed.")
    if not graph.links_recorded:
        notes.append("Internal-link relationships were not recorded for this scan.")
    return notes


def node_to_dict(node: NodeStats) -> dict[str, Any]:
    page = node.page
    return {
        "id": page.id,
        "page_id": page.id,
        "scan_id": page.scan_id,
        "url": page.url,
        "normalized_url": page.normalized_url,
        "final_url": page.final_url,
        "path": node.url_path,
        "title": page.title,
        "h1": page.h1,
        "page_type": page.page_type,
        "page_type_label": page.page_type_label or PAGE_TYPE_LABELS.get((page.page_type or "unknown").lower(), "Unknown"),
        "depth": page.depth,
        "url_path_depth": node.url_path_depth,
        "crawl_status": page.crawl_status,
        "http_status": page.http_status,
        "indexable": page.indexable,
        "canonical_url": page.canonical_url,
        "word_count": page.word_count,
        "issue_count": page.issue_count,
        "severity_counts": page.severity_counts,
        "inbound_link_count": node.inbound_count,
        "outbound_link_count": node.outbound_count,
        "potential_orphan": node.potential_orphan,
        "terminal_page": node.terminal_page,
        "dead_end": node.dead_end,
        "is_seed": page.is_seed,
        "skip_reason": page.skip_reason,
        "failure_reason": page.failure_reason,
    }


def collapse_edges(links: list[InternalLink], allowed_ids: set[str]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for link in links:
        if link.source_page_id not in allowed_ids or link.destination_page_id not in allowed_ids:
            continue
        key = (link.source_page_id, link.destination_page_id)
        bucket = grouped.get(key)
        if bucket is None:
            grouped[key] = {
                "id": f"edge_{link.source_page_id}_{link.destination_page_id}",
                "source": link.source_page_id,
                "target": link.destination_page_id,
                "source_page_id": link.source_page_id,
                "destination_page_id": link.destination_page_id,
                "link_count": 1,
                "anchors": [link.anchor_text] if link.anchor_text else [],
            }
        else:
            bucket["link_count"] += 1
            if link.anchor_text and link.anchor_text not in bucket["anchors"] and len(bucket["anchors"]) < 4:
                bucket["anchors"].append(link.anchor_text)
    return list(grouped.values())


def neighbor_rows(links: list[InternalLink], graph: ArchitectureGraph, *, direction: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for link in links:
        other_id = link.source_page_id if direction == "inbound" else link.destination_page_id
        other = graph.nodes.get(other_id)
        page = other.page if other else None
        rows.append(
            {
                "id": link.id,
                "source_page_id": link.source_page_id,
                "destination_page_id": link.destination_page_id,
                "source_url": link.source_url,
                "destination_url": link.destination_url,
                "anchor_text": link.anchor_text,
                "rel": link.rel,
                "page_id": other_id,
                "title": page.title if page else None,
                "path": url_path(page.normalized_url if page else (link.source_url if direction == "inbound" else link.destination_url)),
                "page_type": page.page_type if page else None,
                "page_type_label": (page.page_type_label if page else None)
                or PAGE_TYPE_LABELS.get(((page.page_type if page else None) or "unknown").lower(), "Unknown"),
            }
        )
    return rows
