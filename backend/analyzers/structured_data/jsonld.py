"""JSON-LD block parsing. Reuses Phase 5 script discovery; does not fetch URLs."""

from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup

from backend.analyzers.structured_data.config import SchemaScoringConfig, DEFAULT_SCORING
from backend.analyzers.structured_data.models import JsonLdBlock, SchemaEntity, SchemaRelationship
from backend.parser.structured_data import json_ld_script_texts, node_text, schema_type_names

COMMENT = re.compile(r"^\s*<!--(.*?)-->\s*$", re.S)
CDATA = re.compile(r"//\s*<!\[CDATA\[|//\s*\]\]>", re.I)
REL_KEYS = (
    "publisher",
    "author",
    "creator",
    "mainEntity",
    "mainEntityOfPage",
    "isPartOf",
    "about",
    "item",
    "itemListElement",
    "image",
    "logo",
    "offers",
    "brand",
    "review",
    "aggregateRating",
    "sameAs",
    "contactPoint",
    "address",
    "organizer",
    "performer",
    "location",
    "provider",
)


def prepare_jsonld_text(raw: str) -> str:
    text = (raw or "").strip()
    match = COMMENT.match(text)
    if match:
        text = match.group(1).strip()
    return CDATA.sub("", text).strip()


def context_label(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list):
        parts = [context_label(item) for item in value[:6]]
        return ", ".join(part for part in parts if part) or None
    if isinstance(value, dict):
        url = value.get("@vocab") or value.get("schema") or value.get("@base")
        if isinstance(url, str) and url.strip():
            return url.strip()
        return "object-context"
    return str(value)[:80]


def preview_value(value: Any, *, depth: int, max_keys: int) -> Any:
    if depth <= 0:
        return "…"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:200]
    if isinstance(value, list):
        return [preview_value(item, depth=depth - 1, max_keys=max_keys) for item in value[:8]]
    if isinstance(value, dict):
        out = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= max_keys:
                out["…"] = f"{len(value) - max_keys} more"
                break
            out[str(key)[:40]] = preview_value(item, depth=depth - 1, max_keys=max_keys)
        return out
    return str(value)[:80]


def serialize_prop(value: Any, limit: int = 120) -> str | None:
    text = node_text(value)
    if text:
        return text[:limit]
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        parts = [serialize_prop(item, limit) for item in value[:6]]
        joined = ", ".join(part for part in parts if part)
        return joined[:limit] if joined else None
    if isinstance(value, dict):
        return node_text(value.get("@id") or value.get("name") or value.get("url") or value.get("headline"))
    return None


def parse_json_ld(
    html_source: str,
    *,
    config: SchemaScoringConfig = DEFAULT_SCORING,
) -> tuple[list[JsonLdBlock], list[SchemaEntity], list[SchemaRelationship], bool]:
    soup = BeautifulSoup(html_source or "", "html.parser")
    scripts = json_ld_script_texts(soup)
    blocks: list[JsonLdBlock] = []
    entities: list[SchemaEntity] = []
    relationships: list[SchemaRelationship] = []
    truncated = False
    entity_seq = 0

    def next_id() -> str:
        nonlocal entity_seq
        entity_seq += 1
        return f"jsonld:{entity_seq}"

    for index, raw in enumerate(scripts):
        prepared = prepare_jsonld_text(raw)
        block_truncated = False
        if len(prepared) > config.max_block_size:
            prepared = prepared[: config.max_block_size]
            block_truncated = True
            truncated = True
        if not prepared:
            blocks.append(JsonLdBlock(index=index, valid=False, error="Empty JSON-LD script."))
            continue
        try:
            payload = json.loads(prepared)
        except json.JSONDecodeError as exc:
            blocks.append(JsonLdBlock(index=index, valid=False, error="Malformed JSON-LD.", truncated=block_truncated))
            continue
        before = len(entities)
        walk(payload, depth=0, block_index=index, parent_id=None, predicate=None, entities=entities, relationships=relationships, next_id=next_id, config=config, truncated_flag={"value": False})
        if len(entities) >= config.max_entities:
            truncated = True
        types: list[str] = []
        seen: set[str] = set()
        for entity in entities[before:]:
            for type_name in entity.types:
                if type_name not in seen:
                    seen.add(type_name)
                    types.append(type_name)
        ctx = None
        if isinstance(payload, dict):
            ctx = context_label(payload.get("@context"))
        elif isinstance(payload, list) and payload and isinstance(payload[0], dict):
            ctx = context_label(payload[0].get("@context"))
        blocks.append(
            JsonLdBlock(
                index=index,
                valid=True,
                truncated=block_truncated,
                context=ctx,
                types=types,
                entity_count=len(entities) - before,
                preview=preview_value(payload, depth=3, max_keys=config.max_preview_keys),
            )
        )
        if len(entities) >= config.max_entities:
            truncated = True
            break
    return blocks, entities, relationships, truncated


def walk(
    node: Any,
    *,
    depth: int,
    block_index: int,
    parent_id: str | None,
    predicate: str | None,
    entities: list[SchemaEntity],
    relationships: list[SchemaRelationship],
    next_id,
    config: SchemaScoringConfig,
    truncated_flag: dict,
) -> str | None:
    if len(entities) >= config.max_entities or depth > config.max_depth:
        truncated_flag["value"] = True
        return None
    if isinstance(node, list):
        last = None
        for item in node:
            last = walk(item, depth=depth + 1, block_index=block_index, parent_id=parent_id, predicate=predicate, entities=entities, relationships=relationships, next_id=next_id, config=config, truncated_flag=truncated_flag)
        return last
    if not isinstance(node, dict):
        if parent_id and predicate:
            relationships.append(SchemaRelationship(source_id=parent_id, predicate=predicate, target_value=str(node)[:160], inline=False))
        return None

    if "@graph" in node:
        walk(node.get("@graph"), depth=depth + 1, block_index=block_index, parent_id=parent_id, predicate=predicate, entities=entities, relationships=relationships, next_id=next_id, config=config, truncated_flag=truncated_flag)

    types = schema_type_names(node)
    node_id = node_text(node.get("@id"))
    extra_keys = [key for key in node.keys() if str(key) not in {"@id", "@type", "@context", "@graph"}]
    if node_id and not types and not extra_keys:
        if parent_id and predicate:
            relationships.append(SchemaRelationship(source_id=parent_id, predicate=predicate, target_value=node_id, inline=False))
        return None
    if types or node_id or extra_keys:
        internal = next_id()
        props: dict[str, str] = {}
        for key, value in node.items():
            if key.startswith("@") or key in {"@graph"}:
                continue
            if len(props) >= config.max_properties:
                break
            serialized = serialize_prop(value)
            if serialized:
                props[str(key)[:40]] = serialized
        name = node_text(node.get("name") or node.get("headline") or node.get("legalName"))
        entities.append(
            SchemaEntity(
                internal_id=internal,
                id=node_id,
                types=types,
                name=name,
                source="json-ld",
                block_index=block_index,
                properties=props,
            )
        )
        if parent_id and predicate:
            relationships.append(SchemaRelationship(source_id=parent_id, predicate=predicate, target_id=internal, target_value=node_id or name, inline=True))
        for rel in REL_KEYS:
            if rel not in node:
                continue
            walk(node[rel], depth=depth + 1, block_index=block_index, parent_id=internal, predicate=rel, entities=entities, relationships=relationships, next_id=next_id, config=config, truncated_flag=truncated_flag)
        return internal

    if parent_id and predicate and node_id:
        relationships.append(SchemaRelationship(source_id=parent_id, predicate=predicate, target_value=node_id, inline=False))
    return None
